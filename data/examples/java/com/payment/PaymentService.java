package com.payment;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Core service for processing payments.
 * Handles payment creation, processing, refunds, and status management.
 */
public class PaymentService {

    private final PaymentRepository repository;
    private final PaymentGateway gateway;
    private final FraudDetectionService fraudService;
    private final NotificationService notificationService;

    public PaymentService(
            PaymentRepository repository,
            PaymentGateway gateway,
            FraudDetectionService fraudService,
            NotificationService notificationService) {
        this.repository = repository;
        this.gateway = gateway;
        this.fraudService = fraudService;
        this.notificationService = notificationService;
    }

    /**
     * Creates and processes a new payment.
     * Performs validation, fraud check, and gateway processing.
     *
     * @param request the payment request details
     * @return the processed payment
     * @throws PaymentException if payment processing fails
     */
    public Payment processPayment(PaymentRequest request) throws PaymentException {
        // Create payment entity
        Payment payment = new Payment(
            request.getCustomerId(),
            request.getAmount(),
            request.getCurrency(),
            request.getMethod()
        );
        payment.setDescription(request.getDescription());
        payment.setMetadata(request.getMetadata());

        // Validate payment
        if (!payment.isValid()) {
            throw new PaymentException("Invalid payment data", "VALIDATION_ERROR");
        }

        // Check for fraud
        FraudCheckResult fraudResult = fraudService.checkPayment(payment);
        if (fraudResult.isHighRisk()) {
            payment.setStatus(PaymentStatus.UNDER_REVIEW);
            repository.save(payment);
            notificationService.notifyFraudReview(payment);
            return payment;
        }

        // Save initial payment
        repository.save(payment);

        // Process through gateway
        try {
            payment.setStatus(PaymentStatus.PROCESSING);
            repository.save(payment);

            GatewayResponse response = gateway.charge(payment);

            if (response.isSuccessful()) {
                payment.markCompleted(response.getTransactionId());
                notificationService.notifyPaymentSuccess(payment);
            } else {
                payment.markFailed(response.getErrorMessage());
                notificationService.notifyPaymentFailure(payment);
            }
        } catch (Exception e) {
            payment.markFailed("Gateway error: " + e.getMessage());
            throw new PaymentException("Payment processing failed", "GATEWAY_ERROR", e);
        } finally {
            repository.save(payment);
        }

        return payment;
    }

    /**
     * Retrieves a payment by its ID.
     *
     * @param paymentId the payment UUID
     * @return the payment if found
     */
    public Optional<Payment> getPayment(UUID paymentId) {
        return repository.findById(paymentId);
    }

    /**
     * Retrieves all payments for a customer.
     *
     * @param customerId the customer identifier
     * @return list of payments
     */
    public List<Payment> getCustomerPayments(String customerId) {
        return repository.findByCustomerId(customerId);
    }

    /**
     * Processes a refund for a completed payment.
     *
     * @param paymentId the payment to refund
     * @param amount the amount to refund (null for full refund)
     * @return the refund result
     * @throws PaymentException if refund fails
     */
    public RefundResult refundPayment(UUID paymentId, BigDecimal amount) throws PaymentException {
        Payment payment = repository.findById(paymentId)
            .orElseThrow(() -> new PaymentException("Payment not found", "NOT_FOUND"));

        if (!payment.getStatus().canRefund()) {
            throw new PaymentException(
                "Cannot refund payment in status: " + payment.getStatus(),
                "INVALID_STATUS"
            );
        }

        BigDecimal refundAmount = amount != null ? amount : payment.getAmount();

        if (refundAmount.compareTo(payment.getAmount()) > 0) {
            throw new PaymentException("Refund amount exceeds payment amount", "INVALID_AMOUNT");
        }

        try {
            GatewayResponse response = gateway.refund(payment.getExternalReference(), refundAmount);

            if (response.isSuccessful()) {
                payment.setStatus(PaymentStatus.REFUNDED);
                repository.save(payment);
                notificationService.notifyRefundSuccess(payment, refundAmount);
                return new RefundResult(true, response.getTransactionId(), refundAmount);
            } else {
                return new RefundResult(false, null, BigDecimal.ZERO, response.getErrorMessage());
            }
        } catch (Exception e) {
            throw new PaymentException("Refund processing failed", "REFUND_ERROR", e);
        }
    }

    /**
     * Cancels a pending payment.
     *
     * @param paymentId the payment to cancel
     * @throws PaymentException if cancellation fails
     */
    public void cancelPayment(UUID paymentId) throws PaymentException {
        Payment payment = repository.findById(paymentId)
            .orElseThrow(() -> new PaymentException("Payment not found", "NOT_FOUND"));

        if (!payment.getStatus().canCancel()) {
            throw new PaymentException(
                "Cannot cancel payment in status: " + payment.getStatus(),
                "INVALID_STATUS"
            );
        }

        payment.setStatus(PaymentStatus.CANCELLED);
        repository.save(payment);
        notificationService.notifyPaymentCancelled(payment);
    }

    /**
     * Approves a payment that is under fraud review.
     *
     * @param paymentId the payment to approve
     * @throws PaymentException if approval fails
     */
    public Payment approveReviewedPayment(UUID paymentId) throws PaymentException {
        Payment payment = repository.findById(paymentId)
            .orElseThrow(() -> new PaymentException("Payment not found", "NOT_FOUND"));

        if (payment.getStatus() != PaymentStatus.UNDER_REVIEW) {
            throw new PaymentException("Payment is not under review", "INVALID_STATUS");
        }

        // Continue processing
        payment.setStatus(PaymentStatus.PROCESSING);
        repository.save(payment);

        GatewayResponse response = gateway.charge(payment);

        if (response.isSuccessful()) {
            payment.markCompleted(response.getTransactionId());
            notificationService.notifyPaymentSuccess(payment);
        } else {
            payment.markFailed(response.getErrorMessage());
            notificationService.notifyPaymentFailure(payment);
        }

        repository.save(payment);
        return payment;
    }
}
