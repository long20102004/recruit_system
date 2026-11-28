package recruit.demo;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
@SpringBootApplication
@org.springframework.scheduling.annotation.EnableScheduling
public class InterviewApplication {
    public static void main(String[] args) { SpringApplication.run(InterviewApplication.class, args); }
}
