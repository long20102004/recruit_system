package recruit.demo.storage;

import recruit.demo.dto.FileLinkDto;

/** Lưu file lên object storage (R2). Key do {@link ObjectKeys} sinh ra; DB chỉ lưu key. */
public interface StorageService {

    /** Ghi vào bucket private (CV, giấy phép). */
    void putPrivate(String key, byte[] content, String contentType);

    /** Ghi vào bucket public (ảnh). */
    void putPublic(String key, byte[] content, String contentType);

    /**
     * URL ký tạm để tải object private.
     *
     * @param fileName tên file gốc hiển thị khi tải về
     * @param inline   true: mở trong trình duyệt; false: tải xuống
     */
    FileLinkDto presignGet(String key, String fileName, boolean inline);

    /** URL công khai của object trong bucket public; key rỗng trả null. */
    String publicUrl(String key);

    /** Xoá object private; lỗi chỉ ghi log. */
    void deletePrivateQuietly(String key);

    /** Xoá object public; lỗi chỉ ghi log. */
    void deletePublicQuietly(String key);
}
