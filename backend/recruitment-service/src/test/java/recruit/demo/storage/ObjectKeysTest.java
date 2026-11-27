package recruit.demo.storage;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class ObjectKeysTest {

    @Test
    void keysFollowConvention() {
        assertTrue(ObjectKeys.cv(7, 2).matches("cvs/7/2/[0-9a-f-]{36}\\.pdf"));
        assertTrue(ObjectKeys.companyFile(5, "logo", "Logo Cty.JPEG").matches("companies/5/logo/[0-9a-f-]{36}\\.jpeg"));
        assertTrue(ObjectKeys.companyFile(5, "license", "no-ext").matches("companies/5/license/[0-9a-f-]{36}"));
    }

    @Test
    void distinguishesObjectKeysFromLegacyPaths() {
        assertTrue(ObjectKeys.isObjectKey("cvs/7/2/a.pdf"));
        assertTrue(ObjectKeys.isLegacyPath("/app/uploads/a.pdf"));
        assertTrue(ObjectKeys.isLegacyPath("C:\\uploads\\a.pdf"));
        assertFalse(ObjectKeys.isLegacyPath("companies/5/license/a.pdf"));
        assertFalse(ObjectKeys.isLegacyPath(""));
        assertFalse(ObjectKeys.isLegacyPath(null));
    }

    @Test
    void extensionIsSanitized() {
        assertEquals(".pdf", ObjectKeys.extension("a.PDF"));
        assertEquals("", ObjectKeys.extension("a."));
        assertEquals("", ObjectKeys.extension("a.verylongextension"));
        assertEquals(".png", ObjectKeys.extension("../x.p/n\"g"));
    }
}
