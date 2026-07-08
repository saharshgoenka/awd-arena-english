package com.finledger.controller;

import com.finledger.model.User;
import com.finledger.repository.UserRepository;
import jakarta.servlet.http.HttpSession;

import java.util.Optional;

public final class SessionAuth {

    private SessionAuth() {}

    public static Optional<User> currentUser(HttpSession session, UserRepository userRepository) {
        Object username = session.getAttribute("username");
        if (!(username instanceof String value) || value.isBlank()) {
            return Optional.empty();
        }
        return userRepository.findByUsername(value);
    }
}
