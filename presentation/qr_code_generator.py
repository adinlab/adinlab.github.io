from PIL import ImageOps
import qrcode


def generate_qr(url: str, output_path: str) -> None:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=0,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
    img = ImageOps.crop(img, border=0)
    img.save(output_path)
    print(f"QR code saved to: {output_path}")


if __name__ == "__main__":
    generate_qr("https://adinlab.github.io/", "assets/img/adinlab.png")
    generate_qr("https://github.com/adinlab/objectrl", "assets/img/objectrl.png")
