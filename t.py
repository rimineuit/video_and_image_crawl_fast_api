import ffmpeg

input_file = r"E:\Test_crawlee\input.mp3"
output_file = r"E:\Test_crawlee\output_cut.mp3"

# Thời gian: bắt đầu = 1 phút 30, kết thúc = 3 phút 45
start_time = "00:01:30"
duration = "00:02:15"  # 3:45 - 1:30 = 2 phút 15 giây

# Cắt đoạn và xuất file mới
ffmpeg.input(input_file, ss=start_time, t=duration).output(output_file).run()

print("✅ Đã cắt và lưu file mới!")
