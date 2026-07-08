package com.finledger.controller;

import com.finledger.model.User;
import com.finledger.repository.UserRepository;
import jakarta.servlet.http.HttpSession;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Map;

@RestController
public class AuthController {

    @Autowired
    private UserRepository userRepository;

    @PostMapping("/api/auth/login")
    public ResponseEntity<?> login(@RequestBody Map<String, String> body, HttpSession session) {
        String username = body.getOrDefault("username", "");
        String password = body.getOrDefault("password", "");

        User user = userRepository.findByUsername(username).orElse(null);
        if (user == null) {
            return ResponseEntity.status(401).body(Map.of("success", false, "error", "Unknown username"));
        }
        if (!md5Hex(password).equalsIgnoreCase(user.getPasswordHash())) {
            return ResponseEntity.status(401).body(Map.of("success", false, "error", "Invalid password"));
        }

        session.setAttribute("username", user.getUsername());
        return ResponseEntity.ok(Map.of("success", true, "role", user.getRole()));
    }

    @PostMapping("/api/auth/logout")
    public ResponseEntity<?> logout(HttpSession session) {
        session.invalidate();
        return ResponseEntity.ok(Map.of("success", true));
    }

    @GetMapping("/api/users/profile")
    public ResponseEntity<?> profile(@RequestParam(defaultValue = "") String username, HttpSession session) {
        var currentUser = SessionAuth.currentUser(session, userRepository);
        if (currentUser.isEmpty()) {
            return ResponseEntity.status(401).body(Map.of("error", "Login required"));
        }

        String lookup = username.isBlank() ? currentUser.get().getUsername() : username;
        User user = userRepository.findByUsername(lookup)
                .orElse(null);
        if (user == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(user);
    }

    private String md5Hex(String value) {
        try {
            MessageDigest md = MessageDigest.getInstance("MD5");
            byte[] digest = md.digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder out = new StringBuilder();
            for (byte b : digest) {
                out.append(String.format("%02x", b));
            }
            return out.toString();
        } catch (Exception e) {
            throw new IllegalStateException("MD5 unavailable", e);
        }
    }
}
