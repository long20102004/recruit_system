package recruit.demo.extraction.fields;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;

/** VN phone regex on synthetic strings only. */
class RegexFieldExtractorPhoneTest {

    @ParameterizedTest
    @CsvSource(delimiter = '|', value = {
            "SĐT: 0912345678 | 0912345678",
            "Phone 0912 345 678, Email | 0912 345 678",
            "0912.345.678 | 0912.345.678",
            "0912-345-678 | 0912-345-678",
            "Tel: +84 912 345 678 | +84 912 345 678",
            "+84 61 5768424 | +84 61 5768424",
            "(+84) 912 345 678 | (+84) 912 345 678",
            "(0377) 386 391 | (0377) 386 391",
    })
    void matchesVietnamesePhones(String text, String expected) {
        assertEquals(expected, RegexFieldExtractor.first(RegexFieldExtractor.VN_PHONE, text).orElse(null));
    }

    @ParameterizedTest
    @ValueSource(strings = {
            "2020 - 2024", "GPA 3.85/4.0", "01/2025 - 03/2025",
            "081057438",          // 9 digits: not a valid VN number
            "09123456789",        // 11 digits
            "id 1234567890",
    })
    void rejectsNonPhones(String text) {
        assertTrue(RegexFieldExtractor.first(RegexFieldExtractor.VN_PHONE, text).isEmpty(), text);
    }
}
