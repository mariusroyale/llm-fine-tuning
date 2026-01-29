package com.payment;

/**
 * Bank account details for bank transfer payments.
 */
public class BankDetails {

    private String accountNumber;
    private String routingNumber;
    private String accountHolderName;
    private String bankName;
    private String accountType;
    private String iban;
    private String swiftCode;

    public BankDetails() {}

    /**
     * Creates bank details for US bank accounts.
     * @param accountNumber the account number
     * @param routingNumber the routing number
     * @param accountHolderName name on account
     */
    public static BankDetails forUS(String accountNumber, String routingNumber, String accountHolderName) {
        BankDetails details = new BankDetails();
        details.accountNumber = accountNumber;
        details.routingNumber = routingNumber;
        details.accountHolderName = accountHolderName;
        return details;
    }

    /**
     * Creates bank details for international transfers.
     * @param iban the IBAN
     * @param swiftCode the SWIFT/BIC code
     * @param accountHolderName name on account
     */
    public static BankDetails forInternational(String iban, String swiftCode, String accountHolderName) {
        BankDetails details = new BankDetails();
        details.iban = iban;
        details.swiftCode = swiftCode;
        details.accountHolderName = accountHolderName;
        return details;
    }

    /**
     * Returns a masked account number for display.
     * @return masked account like "****1234"
     */
    public String getMaskedAccountNumber() {
        if (accountNumber == null || accountNumber.length() < 4) {
            return "****";
        }
        return "****" + accountNumber.substring(accountNumber.length() - 4);
    }

    /**
     * Checks if this is an international (IBAN) account.
     * @return true if IBAN is present
     */
    public boolean isInternational() {
        return iban != null && !iban.isEmpty();
    }

    // Getters and setters
    public String getAccountNumber() { return accountNumber; }
    public void setAccountNumber(String accountNumber) { this.accountNumber = accountNumber; }

    public String getRoutingNumber() { return routingNumber; }
    public void setRoutingNumber(String routingNumber) { this.routingNumber = routingNumber; }

    public String getAccountHolderName() { return accountHolderName; }
    public void setAccountHolderName(String accountHolderName) { this.accountHolderName = accountHolderName; }

    public String getBankName() { return bankName; }
    public void setBankName(String bankName) { this.bankName = bankName; }

    public String getAccountType() { return accountType; }
    public void setAccountType(String accountType) { this.accountType = accountType; }

    public String getIban() { return iban; }
    public void setIban(String iban) { this.iban = iban; }

    public String getSwiftCode() { return swiftCode; }
    public void setSwiftCode(String swiftCode) { this.swiftCode = swiftCode; }
}
