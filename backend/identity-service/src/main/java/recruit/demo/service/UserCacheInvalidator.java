package recruit.demo.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import recruit.demo.security.UserSnapshotCache;

/** Xoá cache tóm tắt người dùng sau khi transaction commit, để không nạp lại dữ liệu cũ. */
@Component
@RequiredArgsConstructor
public class UserCacheInvalidator {

    private final UserSnapshotCache cache;

    public void evictAfterCommit(Integer userId) {
        if (TransactionSynchronizationManager.isSynchronizationActive()) {
            TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
                @Override
                public void afterCommit() {
                    cache.evict(userId);
                }
            });
        } else {
            cache.evict(userId);
        }
    }
}
