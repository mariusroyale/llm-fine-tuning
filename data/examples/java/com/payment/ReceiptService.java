package com.payment;

/**
 * Service for generating and delivering payment receipts.
 */
public class ReceiptService {

    private final MerchantInfo merchantInfo;
    private final NotificationService notificationService;

    public ReceiptService(MerchantInfo merchantInfo, NotificationService notificationService) {
        this.merchantInfo = merchantInfo;
        this.notificationService = notificationService;
    }

    /**
     * Generates a receipt for a completed payment.
     * @param payment the completed payment
     * @return the generated receipt
     */
    public Receipt generateReceipt(Payment payment) {
        if (payment.getStatus() != PaymentStatus.COMPLETED &&
            payment.getStatus() != PaymentStatus.REFUNDED) {
            throw new IllegalStateException("Cannot generate receipt for payment in status: " + payment.getStatus());
        }

        Receipt receipt = Receipt.fromPayment(payment, merchantInfo);
        receipt.generateCustomerCopy();
        receipt.generateMerchantCopy();

        return receipt;
    }

    /**
     * Generates and sends a receipt via email.
     * @param payment the payment
     * @param email customer email address
     * @return the generated receipt
     */
    public Receipt sendReceiptByEmail(Payment payment, String email) {
        Receipt receipt = generateReceipt(payment);

        // Add email to payment metadata
        if (payment.getMetadata() != null) {
            payment.getMetadata().addAttribute("receiptEmail", email);
        }

        notificationService.sendReceipt(payment);

        return receipt;
    }

    /**
     * Generates and sends a receipt via SMS.
     * @param payment the payment
     * @param phoneNumber customer phone number
     * @return the generated receipt
     */
    public Receipt sendReceiptBySms(Payment payment, String phoneNumber) {
        Receipt receipt = generateReceipt(payment);

        if (payment.getMetadata() != null) {
            payment.getMetadata().addAttribute("receiptPhone", phoneNumber);
        }

        notificationService.sendReceipt(payment);

        return receipt;
    }

    /**
     * Gets the receipt text formatted for printing.
     * @param receipt the receipt to format
     * @param includeMerchantCopy include merchant copy
     * @return printable text
     */
    public String formatForPrinting(Receipt receipt, boolean includeMerchantCopy) {
        StringBuilder sb = new StringBuilder();

        sb.append(receipt.generateCustomerCopy());

        if (includeMerchantCopy) {
            sb.append("\n\n");
            sb.append("----------------------------------------\n");
            sb.append("              CUT HERE\n");
            sb.append("----------------------------------------\n");
            sb.append("\n\n");
            sb.append(receipt.generateMerchantCopy());
        }

        return sb.toString();
    }

    public MerchantInfo getMerchantInfo() {
        return merchantInfo;
    }
}
