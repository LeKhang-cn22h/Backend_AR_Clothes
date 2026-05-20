# Body Templates

Folder chứa ảnh template full body dùng cho face swap khi user upload ảnh chỉ có mặt.

## Files cần có

- `male_template.jpg`     — nam, đứng thẳng, full body
- `female_template.jpg`   — nữ, đứng thẳng, full body
- `neutral_template.jpg`  — fallback (có thể trùng male hoặc female)

## Yêu cầu ảnh

- Đứng thẳng, mặt nhìn thẳng, full body (đầu → chân)
- Nền đơn giản (trắng/xám)
- Tỷ lệ gần 3:4 hoặc 768×1024
- Mặc áo phông trơn, quần dài đơn giản (để FitDiT thay đồ dễ)

`FaceSwapService.get_body_template(gender)` sẽ load theo thứ tự:
1. `{gender}_template.jpg|png`
2. `neutral_template.jpg`
3. `male_template.jpg` / `female_template.jpg`
