package recruit.demo.service.cv;

import java.util.Locale;
import java.util.Optional;

/** Định dạng tệp CV được hỗ trợ khi ứng viên tải lên. */
public enum CvFileType {
    PDF(".pdf", "application/pdf"),
    DOCX(".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document");

    private final String extension;
    private final String contentType;

    CvFileType(String extension, String contentType) {
        this.extension = extension;
        this.contentType = contentType;
    }

    public String getExtension() {
        return extension;
    }

    public String getContentType() {
        return contentType;
    }

    public static Optional<CvFileType> fromFileName(String name) {
        if (name == null) return Optional.empty();
        String lower = name.toLowerCase(Locale.ROOT);
        for (CvFileType type : values()) {
            if (lower.endsWith(type.extension)) {
                return Optional.of(type);
            }
        }
        return Optional.empty();
    }
}
