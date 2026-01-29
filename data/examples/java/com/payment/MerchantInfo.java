package com.payment;

/**
 * Merchant information for receipts and transaction records.
 */
public class MerchantInfo {

    private String merchantId;
    private String name;
    private String dbaName;
    private String address;
    private String city;
    private String state;
    private String zipCode;
    private String phone;
    private String email;
    private String website;
    private String taxId;
    private String mcc;

    public MerchantInfo() {}

    public MerchantInfo(String merchantId, String name, String address) {
        this.merchantId = merchantId;
        this.name = name;
        this.address = address;
    }

    /**
     * Gets the formatted full address.
     * @return formatted address
     */
    public String getFullAddress() {
        StringBuilder sb = new StringBuilder();
        if (address != null) sb.append(address);
        if (city != null) {
            if (sb.length() > 0) sb.append(", ");
            sb.append(city);
        }
        if (state != null) {
            if (sb.length() > 0) sb.append(", ");
            sb.append(state);
        }
        if (zipCode != null) {
            if (sb.length() > 0) sb.append(" ");
            sb.append(zipCode);
        }
        return sb.toString();
    }

    /**
     * Gets the display name (DBA name if available, otherwise legal name).
     * @return display name
     */
    public String getDisplayName() {
        return dbaName != null && !dbaName.isEmpty() ? dbaName : name;
    }

    // Getters and setters
    public String getMerchantId() { return merchantId; }
    public void setMerchantId(String merchantId) { this.merchantId = merchantId; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getDbaName() { return dbaName; }
    public void setDbaName(String dbaName) { this.dbaName = dbaName; }

    public String getAddress() { return address; }
    public void setAddress(String address) { this.address = address; }

    public String getCity() { return city; }
    public void setCity(String city) { this.city = city; }

    public String getState() { return state; }
    public void setState(String state) { this.state = state; }

    public String getZipCode() { return zipCode; }
    public void setZipCode(String zipCode) { this.zipCode = zipCode; }

    public String getPhone() { return phone; }
    public void setPhone(String phone) { this.phone = phone; }

    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }

    public String getWebsite() { return website; }
    public void setWebsite(String website) { this.website = website; }

    public String getTaxId() { return taxId; }
    public void setTaxId(String taxId) { this.taxId = taxId; }

    public String getMcc() { return mcc; }
    public void setMcc(String mcc) { this.mcc = mcc; }
}
