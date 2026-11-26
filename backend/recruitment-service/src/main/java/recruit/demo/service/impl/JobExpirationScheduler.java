package recruit.demo.service.impl;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;
import recruit.demo.entity.Job;
import recruit.demo.enums.JobStatus;
import recruit.demo.repository.JobRepository;
import recruit.demo.service.cvmatch.CvMatchEvents;

import java.time.LocalDateTime;
import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
public class JobExpirationScheduler {

    private final JobRepository jobRepository;
    private final ApplicationEventPublisher events;

    @Scheduled(fixedDelayString = "${app.jobs.expire-check-ms:300000}")
    @Transactional
    public void expireOverdueJobs() {
        List<Job> overdue = jobRepository.findByStatusAndDeadlineBefore(JobStatus.PUBLISHED, LocalDateTime.now());
        if (overdue.isEmpty()) {
            return;
        }
        for (Job job : overdue) {
            job.setStatus(JobStatus.EXPIRED);
            jobRepository.save(job);
            events.publishEvent(new CvMatchEvents.JobChanged(job.getId()));
        }
        log.info("Marked {} overdue published jobs as EXPIRED", overdue.size());
    }
}
