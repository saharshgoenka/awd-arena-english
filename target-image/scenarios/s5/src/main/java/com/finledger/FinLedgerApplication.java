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
            // Only flag_4 is stored in the DB — it is the flag reachable via the
            // ledger-search UNION SQLi. Seeding all five let one injection dump
            // every flag at once; the others are now served from env by their
            // own controllers.
            String envVal = System.getenv("FLAG_4");
            String value = (envVal != null && !envVal.isEmpty()) ? envVal : placeholder;
            Flag flag = flagRepository.findByName("flag_4").orElseGet(() -> new Flag("flag_4", placeholder));
            flag.setValue(value);
            flagRepository.save(flag);
        };
    }
}
