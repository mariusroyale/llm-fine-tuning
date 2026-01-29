package com.payment;

/**
 * Capabilities of a payment terminal device.
 * Describes what payment methods the Android device supports.
 */
public class TerminalCapabilities {

    private boolean nfcEnabled;
    private boolean magneticStripeReader;
    private boolean chipReader;
    private boolean manualEntry;
    private boolean pinEntry;
    private boolean signatureCapture;
    private boolean receiptPrinting;
    private boolean barcodeScanning;
    private String nfcChipset;
    private int androidSdkVersion;

    public TerminalCapabilities() {}

    /**
     * Creates capabilities for a standard tap-to-pay Android device.
     * @param androidSdkVersion the device's Android SDK version
     * @return standard capabilities
     */
    public static TerminalCapabilities forTapToPay(int androidSdkVersion) {
        TerminalCapabilities caps = new TerminalCapabilities();
        caps.nfcEnabled = true;
        caps.manualEntry = true;
        caps.signatureCapture = true;
        caps.androidSdkVersion = androidSdkVersion;
        return caps;
    }

    /**
     * Creates capabilities for a full POS terminal.
     * @return full POS capabilities
     */
    public static TerminalCapabilities forFullPOS() {
        TerminalCapabilities caps = new TerminalCapabilities();
        caps.nfcEnabled = true;
        caps.magneticStripeReader = true;
        caps.chipReader = true;
        caps.manualEntry = true;
        caps.pinEntry = true;
        caps.signatureCapture = true;
        caps.receiptPrinting = true;
        caps.barcodeScanning = true;
        return caps;
    }

    /**
     * Checks if the device meets minimum requirements for tap-to-pay.
     * @return true if tap-to-pay capable
     */
    public boolean meetsTapToPayRequirements() {
        // Android 9+ (API 28) required for tap-to-pay
        return nfcEnabled && androidSdkVersion >= 28;
    }

    // Getters and setters
    public boolean isNfcEnabled() { return nfcEnabled; }
    public void setNfcEnabled(boolean nfcEnabled) { this.nfcEnabled = nfcEnabled; }

    public boolean hasMagneticStripeReader() { return magneticStripeReader; }
    public void setMagneticStripeReader(boolean magneticStripeReader) {
        this.magneticStripeReader = magneticStripeReader;
    }

    public boolean hasChipReader() { return chipReader; }
    public void setChipReader(boolean chipReader) { this.chipReader = chipReader; }

    public boolean hasManualEntry() { return manualEntry; }
    public void setManualEntry(boolean manualEntry) { this.manualEntry = manualEntry; }

    public boolean hasPinEntry() { return pinEntry; }
    public void setPinEntry(boolean pinEntry) { this.pinEntry = pinEntry; }

    public boolean hasSignatureCapture() { return signatureCapture; }
    public void setSignatureCapture(boolean signatureCapture) {
        this.signatureCapture = signatureCapture;
    }

    public boolean hasReceiptPrinting() { return receiptPrinting; }
    public void setReceiptPrinting(boolean receiptPrinting) {
        this.receiptPrinting = receiptPrinting;
    }

    public boolean hasBarcodeScanning() { return barcodeScanning; }
    public void setBarcodeScanning(boolean barcodeScanning) {
        this.barcodeScanning = barcodeScanning;
    }

    public String getNfcChipset() { return nfcChipset; }
    public void setNfcChipset(String nfcChipset) { this.nfcChipset = nfcChipset; }

    public int getAndroidSdkVersion() { return androidSdkVersion; }
    public void setAndroidSdkVersion(int androidSdkVersion) {
        this.androidSdkVersion = androidSdkVersion;
    }
}
