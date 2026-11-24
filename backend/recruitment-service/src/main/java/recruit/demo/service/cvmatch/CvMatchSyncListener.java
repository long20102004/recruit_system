package recruit.demo.service.cvmatch;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;

/**
 * Dong bo sau khi giao dich da commit (khong bao gio lam hong upload / tao job) va chay nen: nap CV vao cvmatch
 * mat ~2 s tren CPU (plan I01), nguoi dung khong phai cho.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class CvMatchSyncListener {
    private final CvMatchSync sync;

    @Async
    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT, fallbackExecution = true)
    public void onCvChanged(CvMatchEvents.CvChanged ev) {
        if (!sync.enabled()) return;
        try {
            sync.syncCandidate(ev.candidateId());
        } catch (RuntimeException ex) {             // khong de loi lot ra luong nen; scheduler thu lai
            log.warn("cvmatch sync CV candidate={} loi: {}", ev.candidateId(), ex.toString());
        }
    }

    @Async
    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT, fallbackExecution = true)
    public void onJobChanged(CvMatchEvents.JobChanged ev) {
        if (!sync.enabled()) return;
        try {
            sync.syncJob(ev.jobId());
        } catch (RuntimeException ex) {
            log.warn("cvmatch sync JD job={} loi: {}", ev.jobId(), ex.toString());
        }
    }

    @Scheduled(fixedDelayString = "${app.cvmatch.sync.retry-interval-ms:60000}",
            initialDelayString = "${app.cvmatch.sync.retry-interval-ms:60000}")
    public void retry() {
        try {
            int n = sync.retryDue();
            if (n > 0) log.info("cvmatch sync: thu lai {} muc", n);
        } catch (RuntimeException ex) {
            log.warn("cvmatch sync retry loi: {}", ex.toString());
        }
    }
}
