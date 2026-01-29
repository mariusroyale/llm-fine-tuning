package com.payment;

import java.math.BigDecimal;

/**
 * Chase Gempay payment gateway implementation.
 * Handles communication with Chase Gempay API for tap-to-pay processing on Android.
 */
public class ChaseGempayGateway implements PaymentGateway {

    private final String merchantId;
    private final String apiKey;
    private final String apiSecret;
    private final GempayEnvironment environment;
    private final Terminal terminal;

    public ChaseGempayGateway(String merchantId, String apiKey, String apiSecret, GempayEnvironment environment) {
        this.merchantId = merchantId;
        this.apiKey = apiKey;
        this.apiSecret = apiSecret;
        this.environment = environment;
        this.terminal = null;
    }

    public ChaseGempayGateway(String merchantId, String apiKey, String apiSecret,
                              GempayEnvironment environment, Terminal terminal) {
        this.merchantId = merchantId;
        this.apiKey = apiKey;
        this.apiSecret = apiSecret;
        this.environment = environment;
        this.terminal = terminal;
    }

    @Override
    public GatewayResponse charge(Payment payment) throws PaymentGatewayException {
        validatePayment(payment);
        validateTerminalForTapToPay(payment);

        try {
            // Build Gempay charge request
            GempayChargeRequest request = buildChargeRequest(payment);

            // In real implementation, this would call Chase Gempay API
            // POST https://api.chase.com/gempay/v1/charges

            if (environment == GempayEnvironment.SANDBOX) {
                return simulateSandboxResponse(payment);
            }

            // Production API call would go here
            String transactionId = "gempay_" + generateTransactionId();
            String authCode = generateAuthCode();

            GatewayResponse response = GatewayResponse.success(transactionId, authCode);
            response.setRawResponse(request.toJson());

            return response;

        } catch (Exception e) {
            throw new PaymentGatewayException(
                "Failed to process Chase Gempay charge: " + e.getMessage(),
                getProviderName(),
                e
            );
        }
    }

    @Override
    public GatewayResponse refund(String transactionId, BigDecimal amount) throws PaymentGatewayException {
        if (transactionId == null || !transactionId.startsWith("gempay_")) {
            throw new PaymentGatewayException(
                "Invalid transaction ID for refund",
                getProviderName(),
                GempayErrorCode.INVALID_TRANSACTION_ID.getCode()
            );
        }

        try {
            String refundId = "gempay_ref_" + generateTransactionId();
            return GatewayResponse.success(refundId, null);

        } catch (Exception e) {
            throw new PaymentGatewayException(
                "Failed to process Chase Gempay refund: " + e.getMessage(),
                getProviderName(),
                e
            );
        }
    }

    @Override
    public GatewayResponse voidTransaction(String transactionId) throws PaymentGatewayException {
        if (transactionId == null) {
            throw new PaymentGatewayException(
                "Transaction ID required for void",
                getProviderName()
            );
        }

        try {
            String voidId = "gempay_void_" + generateTransactionId();
            return GatewayResponse.success(voidId, null);

        } catch (Exception e) {
            throw new PaymentGatewayException(
                "Failed to void transaction: " + e.getMessage(),
                getProviderName(),
                e
            );
        }
    }

    @Override
    public TransactionStatus getTransactionStatus(String transactionId) {
        if (transactionId == null) {
            return TransactionStatus.UNKNOWN;
        }
        if (transactionId.startsWith("gempay_")) {
            return TransactionStatus.APPROVED;
        }
        return TransactionStatus.UNKNOWN;
    }

    @Override
    public boolean healthCheck() {
        // Ping Chase Gempay API health endpoint
        // GET https://api.chase.com/gempay/v1/health
        return true;
    }

    @Override
    public String getProviderName() {
        return "Chase Gempay";
    }

    /**
     * Processes a tap-to-pay transaction from Android device.
     * @param tapRequest the tap-to-pay request with card data
     * @return gateway response
     */
    public GatewayResponse processTapToPay(TapToPayRequest tapRequest) throws PaymentGatewayException {
        if (terminal == null || !terminal.isRegistered()) {
            throw new PaymentGatewayException(
                "Terminal not registered. Call registerTerminal first.",
                getProviderName(),
                GempayErrorCode.TERMINAL_NOT_REGISTERED.getCode()
            );
        }

        Payment payment = tapRequest.toPayment();
        payment.getMetadata().setProviderName(getProviderName());
        payment.getMetadata().addAttribute("terminalId", terminal.getTerminalId());
        payment.getMetadata().addAttribute("deviceId", terminal.getDeviceId());

        return charge(payment);
    }

    /**
     * Registers the Android device as a terminal with Chase Gempay.
     * @param registration device registration details
     * @return registered terminal
     */
    public Terminal registerTerminal(DeviceRegistration registration) throws PaymentGatewayException {
        validateRegistration(registration);

        try {
            // POST https://api.chase.com/gempay/v1/terminals/register
            String terminalId = "term_" + generateTransactionId();

            Terminal terminal = new Terminal(
                terminalId,
                registration.getDeviceId(),
                registration.getDeviceName(),
                merchantId
            );
            terminal.setStatus(TerminalStatus.ACTIVE);
            terminal.setRegisteredAt(System.currentTimeMillis());

            return terminal;

        } catch (Exception e) {
            throw new PaymentGatewayException(
                "Failed to register terminal: " + e.getMessage(),
                getProviderName(),
                e
            );
        }
    }

    /**
     * Deregisters a terminal from Chase Gempay.
     * @param terminalId the terminal to deregister
     */
    public void deregisterTerminal(String terminalId) throws PaymentGatewayException {
        if (terminalId == null || terminalId.isEmpty()) {
            throw new PaymentGatewayException(
                "Terminal ID required",
                getProviderName()
            );
        }

        // DELETE https://api.chase.com/gempay/v1/terminals/{terminalId}
    }

    private void validatePayment(Payment payment) throws PaymentGatewayException {
        if (payment.getAmount() == null || payment.getAmount().compareTo(BigDecimal.ZERO) <= 0) {
            throw new PaymentGatewayException(
                "Invalid payment amount",
                getProviderName(),
                GempayErrorCode.INVALID_AMOUNT.getCode()
            );
        }
        if (payment.getCurrency() == null || payment.getCurrency().length() != 3) {
            throw new PaymentGatewayException(
                "Invalid currency code",
                getProviderName(),
                GempayErrorCode.INVALID_CURRENCY.getCode()
            );
        }
    }

    private void validateTerminalForTapToPay(Payment payment) throws PaymentGatewayException {
        if (payment.getMethod() != null && payment.getMethod().isTapToPay()) {
            if (terminal == null || !terminal.isRegistered()) {
                throw new PaymentGatewayException(
                    "Tap-to-pay requires a registered terminal",
                    getProviderName(),
                    GempayErrorCode.TERMINAL_NOT_REGISTERED.getCode()
                );
            }
        }
    }

    private void validateRegistration(DeviceRegistration registration) throws PaymentGatewayException {
        if (registration.getDeviceId() == null || registration.getDeviceId().isEmpty()) {
            throw new PaymentGatewayException(
                "Device ID required for registration",
                getProviderName(),
                GempayErrorCode.INVALID_DEVICE_ID.getCode()
            );
        }
    }

    private GempayChargeRequest buildChargeRequest(Payment payment) {
        return new GempayChargeRequest(
            payment.getAmount(),
            payment.getCurrency(),
            merchantId,
            terminal != null ? terminal.getTerminalId() : null,
            payment.getDescription()
        );
    }

    private GatewayResponse simulateSandboxResponse(Payment payment) {
        // Sandbox test scenarios based on amount
        BigDecimal amount = payment.getAmount();

        // Amount ending in .01 = decline
        if (amount.remainder(BigDecimal.ONE).compareTo(new BigDecimal("0.01")) == 0) {
            return GatewayResponse.failure(
                GempayErrorCode.CARD_DECLINED.getCode(),
                "Card declined (sandbox test)"
            );
        }

        // Amount ending in .02 = insufficient funds
        if (amount.remainder(BigDecimal.ONE).compareTo(new BigDecimal("0.02")) == 0) {
            return GatewayResponse.failure(
                GempayErrorCode.INSUFFICIENT_FUNDS.getCode(),
                "Insufficient funds (sandbox test)"
            );
        }

        // Amount > 10000 = require review
        if (amount.compareTo(new BigDecimal("10000")) > 0) {
            return GatewayResponse.pending("gempay_pending_" + generateTransactionId());
        }

        // Default = success
        String transactionId = "gempay_" + generateTransactionId();
        String authCode = generateAuthCode();
        return GatewayResponse.success(transactionId, authCode);
    }

    private String generateTransactionId() {
        return Long.toHexString(System.currentTimeMillis()) +
               Long.toHexString((long) (Math.random() * 1000000));
    }

    private String generateAuthCode() {
        return String.format("%06d", (int) (Math.random() * 1000000));
    }

    public GempayEnvironment getEnvironment() {
        return environment;
    }

    public String getMerchantId() {
        return merchantId;
    }

    public Terminal getTerminal() {
        return terminal;
    }
}
