package com.payment;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * Payment receipt for display and printing.
 * Contains all transaction details formatted for customer receipt.
 */
public class Receipt {

    private String receiptId;
    private String merchantName;
    private String merchantAddress;
    private String merchantPhone;
    private String transactionId;
    private String authorizationCode;
    private LocalDateTime transactionDate;
    private String cardBrand;
    private String maskedCardNumber;
    private String entryMode;
    private BigDecimal subtotal;
    private BigDecimal tipAmount;
    private BigDecimal totalAmount;
    private String currency;
    private PaymentStatus status;
    private String terminalId;
    private String operatorId;
    private String customerCopy;
    private String merchantCopy;

    public Receipt() {
        this.transactionDate = LocalDateTime.now();
        this.receiptId = generateReceiptId();
    }

    /**
     * Creates a receipt from a completed payment.
     * @param payment the completed payment
     * @param merchantInfo merchant details
     * @return formatted receipt
     */
    public static Receipt fromPayment(Payment payment, MerchantInfo merchantInfo) {
        Receipt receipt = new Receipt();

        receipt.merchantName = merchantInfo.getName();
        receipt.merchantAddress = merchantInfo.getAddress();
        receipt.merchantPhone = merchantInfo.getPhone();

        receipt.transactionId = payment.getExternalReference();
        receipt.transactionDate = payment.getCreatedAt();
        receipt.totalAmount = payment.getAmount();
        receipt.currency = payment.getCurrency();
        receipt.status = payment.getStatus();

        if (payment.getMetadata() != null) {
            receipt.cardBrand = payment.getMetadata().getAttribute("cardBrand");
            receipt.maskedCardNumber = "**** " + payment.getMetadata().getAttribute("lastFour");
            receipt.entryMode = payment.getMetadata().getAttribute("entryMode");
            receipt.terminalId = payment.getMetadata().getAttribute("terminalId");

            String tip = payment.getMetadata().getAttribute("tipAmount");
            if (tip != null) {
                receipt.tipAmount = new BigDecimal(tip);
                receipt.subtotal = new BigDecimal(payment.getMetadata().getAttribute("subtotal"));
            }
        }

        return receipt;
    }

    /**
     * Generates the customer copy of the receipt as text.
     * @return formatted receipt text
     */
    public String generateCustomerCopy() {
        StringBuilder sb = new StringBuilder();

        sb.append(centerText(merchantName, 40)).append("\n");
        if (merchantAddress != null) {
            sb.append(centerText(merchantAddress, 40)).append("\n");
        }
        if (merchantPhone != null) {
            sb.append(centerText(merchantPhone, 40)).append("\n");
        }
        sb.append("\n");
        sb.append("========================================\n");
        sb.append("           CUSTOMER COPY\n");
        sb.append("========================================\n\n");

        sb.append(formatLine("Date:", formatDateTime(transactionDate))).append("\n");
        sb.append(formatLine("Transaction:", transactionId != null ? transactionId : "N/A")).append("\n");

        if (authorizationCode != null) {
            sb.append(formatLine("Auth Code:", authorizationCode)).append("\n");
        }

        sb.append("\n");
        sb.append(formatLine("Card:", cardBrand != null ? cardBrand : "Card")).append("\n");
        sb.append(formatLine("Account:", maskedCardNumber != null ? maskedCardNumber : "****")).append("\n");
        sb.append(formatLine("Entry:", entryMode != null ? entryMode : "TAP")).append("\n");

        sb.append("\n");
        sb.append("----------------------------------------\n");

        if (subtotal != null && tipAmount != null) {
            sb.append(formatLine("Subtotal:", formatCurrency(subtotal))).append("\n");
            sb.append(formatLine("Tip:", formatCurrency(tipAmount))).append("\n");
            sb.append("----------------------------------------\n");
        }

        sb.append(formatLine("TOTAL:", formatCurrency(totalAmount))).append("\n");
        sb.append("\n");

        sb.append(centerText(status == PaymentStatus.COMPLETED ? "APPROVED" : status.name(), 40)).append("\n");
        sb.append("\n");
        sb.append(centerText("Thank you!", 40)).append("\n");
        sb.append(centerText("Please retain for your records", 40)).append("\n");

        this.customerCopy = sb.toString();
        return customerCopy;
    }

    /**
     * Generates the merchant copy of the receipt as text.
     * @return formatted receipt text
     */
    public String generateMerchantCopy() {
        StringBuilder sb = new StringBuilder();

        sb.append(centerText(merchantName, 40)).append("\n");
        sb.append("\n");
        sb.append("========================================\n");
        sb.append("           MERCHANT COPY\n");
        sb.append("========================================\n\n");

        sb.append(formatLine("Date:", formatDateTime(transactionDate))).append("\n");
        sb.append(formatLine("Transaction:", transactionId != null ? transactionId : "N/A")).append("\n");
        sb.append(formatLine("Terminal:", terminalId != null ? terminalId : "N/A")).append("\n");

        if (operatorId != null) {
            sb.append(formatLine("Operator:", operatorId)).append("\n");
        }

        sb.append("\n");
        sb.append(formatLine("Card:", cardBrand != null ? cardBrand : "Card")).append("\n");
        sb.append(formatLine("Account:", maskedCardNumber != null ? maskedCardNumber : "****")).append("\n");
        sb.append(formatLine("Entry:", entryMode != null ? entryMode : "TAP")).append("\n");

        sb.append("\n");
        sb.append("----------------------------------------\n");
        sb.append(formatLine("TOTAL:", formatCurrency(totalAmount))).append("\n");
        sb.append("\n");

        sb.append(centerText(status == PaymentStatus.COMPLETED ? "APPROVED" : status.name(), 40)).append("\n");

        sb.append("\n\n");
        sb.append("X_______________________________________\n");
        sb.append(centerText("Cardholder Signature", 40)).append("\n");

        this.merchantCopy = sb.toString();
        return merchantCopy;
    }

    private String formatLine(String label, String value) {
        int spaces = 40 - label.length() - value.length();
        return label + " ".repeat(Math.max(1, spaces)) + value;
    }

    private String centerText(String text, int width) {
        if (text == null) return "";
        int padding = (width - text.length()) / 2;
        return " ".repeat(Math.max(0, padding)) + text;
    }

    private String formatDateTime(LocalDateTime dateTime) {
        if (dateTime == null) return "";
        return dateTime.format(DateTimeFormatter.ofPattern("MM/dd/yyyy hh:mm a"));
    }

    private String formatCurrency(BigDecimal amount) {
        if (amount == null) return "$0.00";
        return String.format("$%.2f", amount);
    }

    private String generateReceiptId() {
        return "RCP" + System.currentTimeMillis();
    }

    // Getters and setters
    public String getReceiptId() { return receiptId; }
    public String getMerchantName() { return merchantName; }
    public void setMerchantName(String merchantName) { this.merchantName = merchantName; }

    public String getMerchantAddress() { return merchantAddress; }
    public void setMerchantAddress(String merchantAddress) { this.merchantAddress = merchantAddress; }

    public String getMerchantPhone() { return merchantPhone; }
    public void setMerchantPhone(String merchantPhone) { this.merchantPhone = merchantPhone; }

    public String getTransactionId() { return transactionId; }
    public void setTransactionId(String transactionId) { this.transactionId = transactionId; }

    public String getAuthorizationCode() { return authorizationCode; }
    public void setAuthorizationCode(String authorizationCode) { this.authorizationCode = authorizationCode; }

    public LocalDateTime getTransactionDate() { return transactionDate; }
    public void setTransactionDate(LocalDateTime transactionDate) { this.transactionDate = transactionDate; }

    public String getCardBrand() { return cardBrand; }
    public void setCardBrand(String cardBrand) { this.cardBrand = cardBrand; }

    public String getMaskedCardNumber() { return maskedCardNumber; }
    public void setMaskedCardNumber(String maskedCardNumber) { this.maskedCardNumber = maskedCardNumber; }

    public String getEntryMode() { return entryMode; }
    public void setEntryMode(String entryMode) { this.entryMode = entryMode; }

    public BigDecimal getSubtotal() { return subtotal; }
    public void setSubtotal(BigDecimal subtotal) { this.subtotal = subtotal; }

    public BigDecimal getTipAmount() { return tipAmount; }
    public void setTipAmount(BigDecimal tipAmount) { this.tipAmount = tipAmount; }

    public BigDecimal getTotalAmount() { return totalAmount; }
    public void setTotalAmount(BigDecimal totalAmount) { this.totalAmount = totalAmount; }

    public String getCurrency() { return currency; }
    public void setCurrency(String currency) { this.currency = currency; }

    public PaymentStatus getStatus() { return status; }
    public void setStatus(PaymentStatus status) { this.status = status; }

    public String getTerminalId() { return terminalId; }
    public void setTerminalId(String terminalId) { this.terminalId = terminalId; }

    public String getOperatorId() { return operatorId; }
    public void setOperatorId(String operatorId) { this.operatorId = operatorId; }
}
