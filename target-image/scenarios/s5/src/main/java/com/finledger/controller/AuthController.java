package com.finledger.controller;

import com.finledger.model.User;
import com.finledger.repository.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
public class AuthController {

    @Autowired
    private UserRepository userRepository;

    // POST /api/auth/login — validates Basic credentials and returns role
    @PostMapping("/api/auth/login")
    public ResponseEntity<?> login(Authentication auth) {
        if (auth == null || !auth.isAuthenticated()) {
            return ResponseEntity.status(401).body(Map.of("success", false));
        }
        return ResponseEntity.ok(Map.of("success", true, "role", auth.getAuthorities().toString()));
    }

    // GET /api/users/profile — flag_3: returns full user including passwordHash
    @GetMapping("/api/users/profile")
    public ResponseEntity<?> profile(Authentication auth) {
        User user = userRepository.findByUsername(auth.getName())
                .orElse(null);
        if (user == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(user);
    }
}
