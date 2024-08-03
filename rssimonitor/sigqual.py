def calculate_signal_quality(rssi, rsrq, rsrp):
    # Normalize the values to a 0-100 scale
    normalized_rssi = normalize_rssi(rssi)
    normalized_rsrq = normalize_rsrq(rsrq)
    normalized_rsrp = normalize_rsrp(rsrp)

    # Assign weights to each metric (adjust these based on your specific needs)
    rssi_weight = 0.3
    rsrq_weight = 0.3
    rsrp_weight = 0.4

    # Calculate the weighted average
    signal_quality = (normalized_rssi * rssi_weight +
                      normalized_rsrq * rsrq_weight +
                      normalized_rsrp * rsrp_weight)

    return signal_quality


def normalize_rssi(rssi):
    # RSSI typically ranges from -120 dBm to -30 dBm
    min_rssi = -120
    max_rssi = -30
    return ((rssi - min_rssi) / (max_rssi - min_rssi)) * 100


def normalize_rsrq(rsrq):
    # RSRQ typically ranges from -19.5 dB to -3 dB
    min_rsrq = -19.5
    max_rsrq = -3
    return ((rsrq - min_rsrq) / (max_rsrq - min_rsrq)) * 100


def normalize_rsrp(rsrp):
    # RSRP typically ranges from -140 dBm to -70 dBm
    min_rsrp = -140
    max_rsrp = -70
    return ((rsrp - min_rsrp) / (max_rsrp - min_rsrp)) * 100
