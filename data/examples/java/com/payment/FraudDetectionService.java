package com.payment;

import java.math.BigDecimal;
import java.util.List;

/**
 * Service for detecting potentially fraudulent payments.
 * Analyzes payment patterns and risk indicators.
 */
public class FraudDetectionService {

    private final PaymentRepository repository;
    private final BigDecimal highValueThreshold;
    private final int velocityLimit;
    private final List<String> blockedCountries;

    public FraudDetectionService(
            PaymentRepository repository,
            BigDecimal highValueThreshold,
            int velocityLimit,
            List<String> blockedCountries) {
        this.repository = repository;
        this.highValueThreshold = highValueThreshold;
        this.velocityLimit = velocityLimit;
        this.blockedCountries = blockedCountries;
    }

    /**
     * Performs fraud analysis on a payment.
     * @param payment the payment to check
     * @return the fraud check result
     */
    public FraudCheckResult checkPayment(Payment payment) {
        FraudCheckResult result = new FraudCheckResult();
        int riskScore = 0;

        // Check for high value transaction
        if (payment.getAmount().compareTo(highValueThreshold) > 0) {
            riskScore += 30;
            result.addRiskFactor("High value transaction");
        }

        // Check velocity (too many transactions in short time)
        List<Payment> recentPayments = repository.findByCustomerId(payment.getCustomerId());
        long recentCount = recentPayments.stream()
            .filter(p -> p.getCreatedAt().isAfter(payment.getCreatedAt().minusHours(1)))
            .count();

        if (recentCount >= velocityLimit) {
            riskScore += 40;
            result.addRiskFactor("Velocity limit exceeded");
        }

        // Check for blocked countries
        if (payment.getMetadata() != null) {
            String country = payment.getMetadata().getAttribute("country");
            if (country != null && blockedCountries.contains(country)) {
                riskScore += 50;
                result.addRiskFactor("Blocked country: " + country);
            }
        }

        // Check for new customer with high value
        if (recentPayments.isEmpty() && payment.getAmount().compareTo(new BigDecimal("500")) > 0) {
            riskScore += 25;
            result.addRiskFactor("New customer high value");
        }

        // Check for mismatched billing info
        if (hasMismatchedBillingInfo(payment)) {
            riskScore += 20;
            result.addRiskFactor("Billing info mismatch");
        }

        result.setRiskScore(riskScore);
        return result;
    }

    /**
     * Checks if billing information appears suspicious.
     */
    private boolean hasMismatchedBillingInfo(Payment payment) {
        if (payment.getMetadata() == null) {
            return false;
        }

        String billingAddress = payment.getMetadata().getBillingAddress();
        String shippingAddress = payment.getMetadata().getShippingAddress();

        if (billingAddress != null && shippingAddress != null) {
            // Simple check - in reality this would be more sophisticated
            return !extractCountry(billingAddress).equals(extractCountry(shippingAddress));
        }

        return false;
    }

    private String extractCountry(String address) {
        if (address == null || address.isEmpty()) {
            return "";
        }
        String[] parts = address.split(",");
        return parts[parts.length - 1].trim();
    }
}
