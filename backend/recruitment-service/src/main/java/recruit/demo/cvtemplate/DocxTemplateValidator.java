package recruit.demo.cvtemplate;

import org.apache.poi.xwpf.usermodel.*;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.multipart.MultipartFile;
import recruit.demo.exception.ApiException;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/**
 * Kiểm tra file mẫu Word (.docx): đuôi file, dung lượng <= 2MB, không chứa VBA macro,
 * mọi ký hiệu {@code {{...}}} nằm trong {@link CvTemplateOptions#SUPPORTED_DOCX_TAGS}
 * và cặp {@code {{?sec}}...{{/sec}}} khớp nhau.
 */
@Component
public class DocxTemplateValidator {

    public static final long MAX_DOCX_BYTES = 2L * 1024 * 1024;
    private static final Pattern TAG_PATTERN = Pattern.compile("\\{\\{(.*?)\\}\\}", Pattern.DOTALL);
    private static final Set<Character> POI_TL_PREFIXES = Set.of('?', '/', '#', '^', '&', '@');

    public byte[] validate(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Vui lòng chọn file Word (.docx)");
        }
        String contentType = file.getContentType();
        if (contentType != null && contentType.toLowerCase(Locale.ROOT).contains("macroenabled")) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Không hỗ trợ file Word chứa macro (.docm)");
        }
        try {
            byte[] bytes = file.getBytes();
            validate(file.getOriginalFilename(), bytes);
            return bytes;
        } catch (IOException ex) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Không đọc được file Word tải lên");
        }
    }

    public void validate(String filename, byte[] bytes) {
        if (filename == null || filename.isBlank()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Tên file không hợp lệ");
        }
        String lowerName = filename.trim().toLowerCase(Locale.ROOT);
        if (lowerName.endsWith(".docm") || !lowerName.endsWith(".docx")) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Chỉ chấp nhận file định dạng .docx (không nhận .docm)");
        }
        if (bytes == null || bytes.length == 0) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "File DOCX rỗng");
        }
        if (bytes.length > MAX_DOCX_BYTES) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "File DOCX vượt quá dung lượng tối đa 2MB");
        }

        checkNoMacroInZip(bytes);
        validateTagsInDocx(bytes);
    }

    private void checkNoMacroInZip(byte[] bytes) {
        boolean hasEntries = false;
        try (ZipInputStream zis = new ZipInputStream(new ByteArrayInputStream(bytes))) {
            ZipEntry entry;
            while ((entry = zis.getNextEntry()) != null) {
                hasEntries = true;
                String name = entry.getName().toLowerCase(Locale.ROOT);
                if (name.endsWith("vbaproject.bin") || name.endsWith(".bin") && name.contains("vba")) {
                    throw new ApiException(HttpStatus.BAD_REQUEST, "Không chấp nhận file DOCX chứa macro VBA");
                }
                if ("[content_types].xml".equals(name)) {
                    byte[] ctBytes = zis.readNBytes(256 * 1024);
                    String ctXml = new String(ctBytes, StandardCharsets.UTF_8).toLowerCase(Locale.ROOT);
                    if (ctXml.contains("macroenabled")) {
                        throw new ApiException(HttpStatus.BAD_REQUEST, "Không chấp nhận file Word chứa macro (.docm)");
                    }
                }
                zis.closeEntry();
            }
        } catch (ApiException ex) {
            throw ex;
        } catch (IOException ex) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "File DOCX không hợp lệ hoặc bị hỏng");
        }
        if (!hasEntries) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "File DOCX không hợp lệ hoặc bị hỏng");
        }
    }

    private void validateTagsInDocx(byte[] bytes) {
        List<String> errors = new ArrayList<>();
        Deque<OpenTag> openStack = new ArrayDeque<>();

        try (XWPFDocument doc = new XWPFDocument(new ByteArrayInputStream(bytes))) {
            int headerIdx = 0;
            for (XWPFHeader header : doc.getHeaderList()) {
                headerIdx++;
                scanBodyElements(header.getBodyElements(), "header #" + headerIdx, openStack, errors);
            }

            scanBodyElements(doc.getBodyElements(), null, openStack, errors);

            int footerIdx = 0;
            for (XWPFFooter footer : doc.getFooterList()) {
                footerIdx++;
                scanBodyElements(footer.getBodyElements(), "footer #" + footerIdx, openStack, errors);
            }
        } catch (ApiException ex) {
            throw ex;
        } catch (Exception ex) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Không đọc được cấu trúc DOCX: file có thể bị hỏng");
        }

        while (!openStack.isEmpty()) {
            OpenTag unclosed = openStack.pop();
            errors.add("Thẻ mở {{?" + unclosed.tagName() + "}} tại " + unclosed.location() + " chưa được đóng");
        }

        if (!errors.isEmpty()) {
            throw new ApiException(HttpStatus.BAD_REQUEST,
                    "File DOCX có ký hiệu không hợp lệ: " + String.join("; ", errors));
        }
    }

    private void scanBodyElements(List<IBodyElement> elements,
                                  String containerPrefix,
                                  Deque<OpenTag> openStack,
                                  List<String> errors) {
        int paraCounter = 0;
        int tableCounter = 0;
        for (IBodyElement elem : elements) {
            if (elem instanceof XWPFParagraph p) {
                paraCounter++;
                String loc = containerPrefix != null
                        ? containerPrefix + ", đoạn #" + paraCounter
                        : "đoạn #" + paraCounter;
                scanText(p.getText(), loc, openStack, errors);
            } else if (elem instanceof XWPFTable table) {
                tableCounter++;
                String tableLoc = containerPrefix != null
                        ? containerPrefix + ", bảng #" + tableCounter
                        : "bảng #" + tableCounter;
                scanTable(table, tableLoc, openStack, errors);
            }
        }
    }

    private void scanTable(XWPFTable table,
                           String tableLoc,
                           Deque<OpenTag> openStack,
                           List<String> errors) {
        int rowIdx = 0;
        for (XWPFTableRow row : table.getRows()) {
            rowIdx++;
            int colIdx = 0;
            for (XWPFTableCell cell : row.getTableCells()) {
                colIdx++;
                String cellLoc = tableLoc + " (dòng " + rowIdx + ", cột " + colIdx + ")";
                scanBodyElements(cell.getBodyElements(), cellLoc, openStack, errors);
            }
        }
    }

    private void scanText(String text,
                          String location,
                          Deque<OpenTag> openStack,
                          List<String> errors) {
        if (text == null || text.isEmpty() || !text.contains("{{")) {
            return;
        }
        Matcher matcher = TAG_PATTERN.matcher(text);
        while (matcher.find()) {
            String raw = matcher.group(1) == null ? "" : matcher.group(1).trim();
            if (raw.isEmpty()) {
                errors.add("Ký hiệu rỗng {{}} tại " + location);
                continue;
            }
            char prefix = 0;
            String tagName = raw;
            if (POI_TL_PREFIXES.contains(raw.charAt(0))) {
                prefix = raw.charAt(0);
                tagName = raw.substring(1).trim();
            }
            if (tagName.isEmpty() || !CvTemplateOptions.SUPPORTED_DOCX_TAGS.contains(tagName)) {
                errors.add("Ký hiệu không hỗ trợ '{{" + raw + "}}' tại " + location);
                continue;
            }
            if (prefix == '?') {
                openStack.push(new OpenTag(tagName, location));
            } else if (prefix == '/') {
                if (openStack.isEmpty()) {
                    errors.add("Thẻ đóng '{{/" + tagName + "}}' không có thẻ mở tại " + location);
                } else if (!openStack.peek().tagName().equals(tagName)) {
                    OpenTag expected = openStack.peek();
                    errors.add("Thẻ đóng '{{/" + tagName + "}}' tại " + location
                            + " không khớp với '{{?" + expected.tagName() + "}}' (" + expected.location() + ")");
                } else {
                    openStack.pop();
                }
            }
        }
    }

    private record OpenTag(String tagName, String location) {}
}
