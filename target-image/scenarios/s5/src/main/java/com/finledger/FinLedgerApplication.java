package com.finledger;

import com.finledger.model.Flag;
import com.finledger.repository.FlagRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@SpringBootApplication
@RestController
public class FinLedgerApplication {

    @Autowired
    private FlagRepository flagRepository;

    public static void main(String[] args) {
        SpringApplication.run(FinLedgerApplication.class, args);
    }

    // Health check — no auth, no DB dependency
    @GetMapping("/health")
    public ResponseEntity<?> health() {
        return ResponseEntity.ok(Map.of("status", "ok"));
    }

    // Seed flags from environment variables before the app serves requests
    @Bean
    public CommandLineRunner seedFlags() {
        return args -> {
            String placeholder = "FLAG{00000000000000000000000000000000}";
            for (int i = 1; i <= 5; i++) {
                String envVal = System.getenv("FLAG_" + i);
                String value = (envVal != null && !envVal.isEmpty()) ? envVal : placeholder;
                String name = "flag_" + i;

                Flag flag = flagRepository.findByName(name).orElseGet(() -> new Flag(name, placeholder));
                flag.setValue(value);
                flagRepository.save(flag);
            }
        };
    }
}
