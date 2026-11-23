package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import recruit.demo.entity.JobSkill;

import java.util.List;

public interface JobSkillRepository extends JpaRepository<JobSkill, Integer> {

    @Query("SELECT js FROM JobSkill js JOIN FETCH js.skill WHERE js.job.id = :jobId")
    List<JobSkill> findByJobId(@Param("jobId") Integer jobId);

    void deleteByJobId(Integer jobId);
}
