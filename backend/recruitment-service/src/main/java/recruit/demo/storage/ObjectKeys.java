package recruit.demo.storage;

import java.util.Locale;
import java.util.UUID;

/** Quy ước object key trên R2 (specs/008-r2-storage). */
public final class ObjectKeys {

    public static final String CV_PREFIX = "cvs/";
    public static final String COMPANY_PREFIX = "companies/";

    private ObjectKeys() {
    }

    /** cvs/{candidateId}/{cvId}/{uuid}.pdf */
    public static String cv(Integer candidateId, Integer cvId) {
        return CV_PREFIX + candidateId + "/" + cvId + "/" + UUID.randomUUID() + ".pdf";
    }

    /** companies/{companyId}/{kind}/{uuid}.{ext}; kind = license | logo | cover. */
    public static String companyFile(Integer companyId, String kind, String originalName) {
        return COMPANY_PREFIX + companyId + "/" + kind + "/" + UUID.randomUUID() + extension(originalName);
    }

    /** Giá trị DB là object key do hệ thống mới sinh (không phải đường dẫn local cũ). */
    public static boolean isObjectKey(String value) {
        return value != null && (value.startsWith(CV_PREFIX) || value.startsWith(COMPANY_PREFIX));
    }

    /** Giá trị DB cũ: đường dẫn file trên đĩa cần migrate. */
    public static boolean isLegacyPath(String value) {
        return value != null && !value.isBlank() && !isObjectKey(value);
    }

    /** ".pdf", ".png"... (chữ thường, chỉ a-z0-9, tối đa 8 ký tự); không có thì rỗng. */
    static String extension(String name) {
        if (name == null) return "";
        int dot = name.lastIndexOf('.');
        if (dot < 0 || dot == name.length() - 1) return "";
        String ext = name.substring(dot + 1).toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]", "");
        if (ext.isEmpty() || ext.length() > 8) return "";
        return "." + ext;
    }
}
