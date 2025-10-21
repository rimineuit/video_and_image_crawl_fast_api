import numpy as np
from itertools import product

# Dữ liệu 9 tháng
data = np.array([1200, 1250, 1100, 1300, 1220, 1310, 1400, 1370, 1420])

# Hàm tính MSE cho bộ trọng số w
def mse_for_weights(w, data):
    preds = []
    for t in range(3, len(data)):  # từ tháng 4 trở đi
        y_hat = w[0]*data[t-3] + w[1]*data[t-2] + w[2]*data[t-1]
        preds.append(y_hat)
    return np.mean(abs(data[3:] - np.array(preds)))

# Lưới tìm kiếm (bước 0.05)
best_w, best_mse = None, float('inf')
for w1, w2 in product(np.arange(0, 1.00, 0.001), repeat=2):
    w3 = 1 - w1 - w2
    if w3 < 0:  # bỏ các tổ hợp không hợp lệ
        continue
    w = np.array([w1, w2, w3])
    mse = mse_for_weights(w, data)
    if mse < best_mse:
        best_mse, best_w = mse, w

print(f"Trọng số tối ưu: w1={best_w[0]:.2f}, w2={best_w[1]:.2f}, w3={best_w[2]:.2f}")
print(f"→ MSE nhỏ nhất: {best_mse:.2f}")
