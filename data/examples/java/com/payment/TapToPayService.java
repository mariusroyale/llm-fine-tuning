package com.payment;

/**
 * Main service for handling tap-to-pay transactions on Android.
 * Orchestrates the complete payment flow from tap to receipt.
 *
 * Flow:
 * 1. Register device/terminal
 * 2. Capture tap-to-pay payment
 * 3. Send to backend
 * 4. Process payment
 * 5. Show receipt
 * 6. Handle errors
 */
public class TapToPayService {

    private final ChaseGempayGateway gateway;
    private final PaymentRepository repository;
    private final ReceiptService receiptService;
    private final FraudDetectionService fraudService;
    private Terminal terminal;

    public TapToPayService(
            ChaseGempayGateway gateway,
            PaymentRepository repository,
            ReceiptService receiptService,
            FraudDetectionService fraudService) {
        this.gateway = gateway;
        this.repository = repository;
        this.receiptService = receiptService;
        this.fraudService = fraudService;
    }

    // =========================================================================
    // STEP 1: Register Device + Terminal
    // =========================================================================

    /**
     * Registers the Android device as a payment terminal with Chase Gempay.
     * Must be called before processing any tap-to-pay transactions.
     *
     * @param registration device registration details
     * @return the registered terminal
     * @throws PaymentGatewayException if registration fails
     */
    public Terminal registerDevice(DeviceRegistration registration) throws PaymentGatewayException {
        // Validate device meets requirements
        if (!registration.isValid()) {
            throw new PaymentGatewayException(
                "Invalid device registration",
                gateway.getProviderName(),
                GempayErrorCode.INVALID_DEVICE_ID.getCode()
            );
        }

        // Check NFC capability
        if (registration.getCapabilities() != null &&
            !registration.getCapabilities().meetsTapToPayRequirements()) {
            throw new PaymentGatewayException(
                "Device does not meet tap-to-pay requirements",
                gateway.getProviderName(),
                GempayErrorCode.NFC_NOT_AVAILABLE.getCode()
            );
        }

        // Register with Chase Gempay
        this.terminal = gateway.registerTerminal(registration);

        return terminal;
    }

    /**
     * Checks if the device is registered and ready for payments.
     * @return true if ready
     */
    public boolean isDeviceRegistered() {
        return terminal != null && terminal.isRegistered();
    }

    /**
     * Gets the current terminal.
     * @return the terminal, or null if not registered
     */
    public Terminal getTerminal() {
        return terminal;
    }

    // =========================================================================
    // STEP 2: Capture Tap-to-Pay Payment
    // =========================================================================

    /**
     * Captures card data from NFC tap.
     * This would be called after the Android NFC reader detects a card.
     *
     * @param encryptedTrackData encrypted card data from NFC
     * @param cardInfo basic card info (brand, last four)
     * @return captured card data
     */
    public TapCardData captureCardData(String encryptedTrackData, String cardBrand, String lastFour) {
        TapCardData cardData = new TapCardData(encryptedTrackData, lastFour, cardBrand);
        return cardData;
    }

    // =========================================================================
    // STEP 3 & 4: Send to Backend + Process Payment
    // =========================================================================

    /**
     * Processes a tap-to-pay transaction.
     * Validates, sends to Chase Gempay, and saves the result.
     *
     * @param request the tap-to-pay request
     * @return the processed payment
     * @throws PaymentException if processing fails
     */
    public TapToPayResult processPayment(TapToPayRequest request) throws PaymentException {
        // Validate terminal is registered
        if (!isDeviceRegistered()) {
            throw new PaymentException(
                "Device not registered. Call registerDevice first.",
                GempayErrorCode.TERMINAL_NOT_REGISTERED.getCode()
            );
        }

        // Validate request
        if (!request.isValid()) {
            throw new PaymentException(
                "Invalid tap-to-pay request",
                GempayErrorCode.INVALID_AMOUNT.getCode()
            );
        }

        // Create payment entity
        Payment payment = request.toPayment();
        payment.setStatus(PaymentStatus.PROCESSING);

        // Run fraud check
        FraudCheckResult fraudResult = fraudService.checkPayment(payment);
        if (fraudResult.isHighRisk()) {
            payment.setStatus(PaymentStatus.UNDER_REVIEW);
            repository.save(payment);

            return TapToPayResult.builder()
                .payment(payment)
                .success(false)
                .requiresReview(true)
                .message("Payment requires review")
                .build();
        }

        // Save initial payment
        repository.save(payment);

        try {
            // Process through Chase Gempay
            GatewayResponse response = gateway.processTapToPay(request);

            if (response.isSuccessful()) {
                payment.markCompleted(response.getTransactionId());
                payment.getMetadata().setProviderTransactionId(response.getTransactionId());

                if (response.getAuthorizationCode() != null) {
                    payment.getMetadata().addAttribute("authCode", response.getAuthorizationCode());
                }
            } else {
                payment.markFailed(response.getErrorMessage());
                payment.getMetadata().setFailureCode(response.getErrorCode());
            }

            repository.save(payment);

            return TapToPayResult.builder()
                .payment(payment)
                .success(response.isSuccessful())
                .transactionId(response.getTransactionId())
                .authorizationCode(response.getAuthorizationCode())
                .errorCode(response.getErrorCode())
                .message(response.isSuccessful() ? "Payment approved" : response.getErrorMessage())
                .build();

        } catch (PaymentGatewayException e) {
            payment.markFailed(e.getMessage());
            repository.save(payment);

            GempayErrorCode errorCode = GempayErrorCode.fromCode(e.getGatewayErrorCode());

            throw new PaymentException(
                errorCode.getUserFriendlyMessage(),
                e.getGatewayErrorCode(),
                e
            );
        }
    }

    // =========================================================================
    // STEP 5: Show Receipt
    // =========================================================================

    /**
     * Generates a receipt for a completed payment.
     *
     * @param payment the completed payment
     * @return the generated receipt
     */
    public Receipt generateReceipt(Payment payment) {
        return receiptService.generateReceipt(payment);
    }

    /**
     * Sends receipt to customer via email.
     *
     * @param payment the payment
     * @param email customer email
     * @return the receipt
     */
    public Receipt sendReceipt(Payment payment, String email) {
        return receiptService.sendReceiptByEmail(payment, email);
    }

    /**
     * Gets the receipt formatted for on-screen display.
     *
     * @param payment the payment
     * @return receipt text
     */
    public String getReceiptForDisplay(Payment payment) {
        Receipt receipt = generateReceipt(payment);
        return receipt.generateCustomerCopy();
    }

    // =========================================================================
    // STEP 6: Handle Errors
    // =========================================================================

    /**
     * Handles a payment error and returns user-friendly message.
     *
     * @param exception the payment exception
     * @return user-friendly error message
     */
    public String handleError(PaymentException exception) {
        GempayErrorCode errorCode = GempayErrorCode.fromCode(exception.getErrorCode());
        return errorCode.getUserFriendlyMessage();
    }

    /**
     * Checks if an error is retryable.
     *
     * @param exception the payment exception
     * @return true if the operation can be retried
     */
    public boolean isRetryableError(PaymentException exception) {
        GempayErrorCode errorCode = GempayErrorCode.fromCode(exception.getErrorCode());
        return errorCode.isRetryable();
    }

    /**
     * Gets suggested action for an error.
     *
     * @param exception the payment exception
     * @return suggested action for the user/operator
     */
    public String getSuggestedAction(PaymentException exception) {
        GempayErrorCode errorCode = GempayErrorCode.fromCode(exception.getErrorCode());

        if (errorCode.isCardError()) {
            return "Ask customer to try a different card";
        }
        if (errorCode.isTapError()) {
            return "Ask customer to tap their card again";
        }
        if (errorCode.isTerminalError()) {
            return "Check device registration and try again";
        }
        if (errorCode.isRetryable()) {
            return "Wait a moment and try again";
        }

        return "Contact support if the issue persists";
    }

    // =========================================================================
    // Additional Operations
    // =========================================================================

    /**
     * Voids a pending or completed payment.
     *
     * @param paymentId the payment to void
     * @return the voided payment
     */
    public Payment voidPayment(String paymentId) throws PaymentException {
        Payment payment = repository.findById(java.util.UUID.fromString(paymentId))
            .orElseThrow(() -> new PaymentException("Payment not found", "NOT_FOUND"));

        try {
            GatewayResponse response = gateway.voidTransaction(payment.getExternalReference());

            if (response.isSuccessful()) {
                payment.setStatus(PaymentStatus.CANCELLED);
                repository.save(payment);
            }

            return payment;
        } catch (PaymentGatewayException e) {
            throw new PaymentException("Failed to void payment", e.getGatewayErrorCode(), e);
        }
    }

    /**
     * Deregisters the terminal when the app is uninstalled or reset.
     */
    public void deregisterDevice() throws PaymentGatewayException {
        if (terminal != null && terminal.getTerminalId() != null) {
            gateway.deregisterTerminal(terminal.getTerminalId());
            terminal = null;
        }
    }
}
