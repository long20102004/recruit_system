package recruit.demo.storage;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import recruit.demo.entity.Company;
import recruit.demo.entity.CvData;
import recruit.demo.repository.CompanyRepository;
import recruit.demo.repository.CvDataRepository;
import recruit.demo.service.CvService;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** File tạm tổng hợp, storage mock. */
class LegacyFileMigrationRunnerTest {

    @Test
    void movesLocalFilesSkipsKeysAndCountsMissing(@TempDir Path dir) throws Exception {
        Path cvFile = Files.write(dir.resolve("old.pdf"), new byte[]{1, 2});
        Path license = Files.write(dir.resolve("gpkd.pdf"), new byte[]{3});
        CvData legacy = CvData.builder().candidateId(7).cvId(2).field(CvService.FILE_URL).value(cvFile.toString()).build();
        CvData already = CvData.builder().candidateId(7).cvId(3).field(CvService.FILE_URL).value("cvs/7/3/x.pdf").build();
        CvData gone = CvData.builder().candidateId(8).cvId(4).field(CvService.FILE_URL).value(dir.resolve("gone.pdf").toString()).build();
        Company company = Company.builder().id(5).licenseFileName("gpkd.pdf").licenseFileUrl(license.toString()).build();

        CvDataRepository cvData = mock(CvDataRepository.class);
        CompanyRepository companies = mock(CompanyRepository.class);
        StorageService storage = mock(StorageService.class);
        when(cvData.findAllByField(CvService.FILE_URL)).thenReturn(List.of(legacy, already, gone));
        when(companies.findAll()).thenReturn(List.of(company));

        var result = new LegacyFileMigrationRunner(cvData, companies, storage).migrate();

        assertEquals(2, result.moved());
        assertEquals(1, result.missing());
        assertEquals(0, result.failed());
        assertTrue(legacy.getValue().startsWith("cvs/7/2/"));
        assertEquals("cvs/7/3/x.pdf", already.getValue());
        assertTrue(company.getLicenseFileUrl().startsWith("companies/5/license/"));
        verify(storage).putPrivate(eq(legacy.getValue()), eq(new byte[]{1, 2}), eq("application/pdf"));
        verify(storage).putPrivate(eq(company.getLicenseFileUrl()), eq(new byte[]{3}), any());
        verify(cvData, times(1)).save(any());

        // Chạy lại: không còn gì để chuyển.
        assertEquals(0, new LegacyFileMigrationRunner(cvData, companies, storage).migrate().moved());
    }
}
