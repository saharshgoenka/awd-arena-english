package com.finledger.repository;

import com.finledger.model.Flag;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.Optional;

@Repository
public interface FlagRepository extends JpaRepository<Flag, Long> {
    Optional<Flag> findByName(String name);
}
