package recruit.demo.service.cvmatch;

/** Su kien phat cuoi giao dich luu CV / job; {@link CvMatchSyncListener} dong bo sau khi commit. */
public final class CvMatchEvents {
    private CvMatchEvents() {
    }

    public record CvChanged(Integer candidateId) {
    }

    public record JobChanged(Integer jobId) {
    }
}
