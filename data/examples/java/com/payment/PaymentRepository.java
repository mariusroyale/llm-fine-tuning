package com.payment;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Repository interface for payment persistence operations.
 * Provides CRUD operations and query methods for payments.
 */
public interface PaymentRepository {

    /**
     * Saves a payment to the database.
     * @param payment the payment to save
     * @return the saved payment
     */
    Payment save(Payment payment);

    /**
     * Finds a payment by its unique ID.
     * @param id the payment UUID
     * @return the payment if found
     */
    Optional<Payment> findById(UUID id);

    /**
     * Finds all payments for a specific customer.
     * @param customerId the customer identifier
     * @return list of customer payments
     */
    List<Payment> findByCustomerId(String customerId);

    /**
     * Finds all payments with a specific status.
     * @param status the payment status
     * @return list of payments with that status
     */
    List<Payment> findByStatus(PaymentStatus status);

    /**
     * Finds payments created within a date range.
     * @param start the start date
     * @param end the end date
     * @return list of payments in the range
     */
    List<Payment> findByCreatedAtBetween(LocalDateTime start, LocalDateTime end);

    /**
     * Finds payments by external reference.
     * @param externalReference the provider reference
     * @return the payment if found
     */
    Optional<Payment> findByExternalReference(String externalReference);

    /**
     * Counts payments by status.
     * @param status the payment status
     * @return count of payments
     */
    long countByStatus(PaymentStatus status);

    /**
     * Deletes a payment by ID.
     * @param id the payment UUID
     */
    void deleteById(UUID id);

    /**
     * Finds all pending payments older than a threshold for cleanup.
     * @param threshold the age threshold
     * @return list of stale pending payments
     */
    List<Payment> findStalePendingPayments(LocalDateTime threshold);
}
