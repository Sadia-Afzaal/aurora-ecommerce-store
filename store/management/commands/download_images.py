import mimetypes
import time
from urllib.request import Request, urlopen

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from store.models import Product


class Command(BaseCommand):
    help = (
        "Download each product's remote image_url into the local media folder "
        "and attach it as the product image (so the site works fully offline)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-download even if a product already has a local image file.",
        )

    def handle(self, *args, **options):
        force = options["force"]
        products = Product.objects.exclude(image_url="")
        downloaded, skipped, failed = 0, 0, 0

        for product in products:
            if product.image and not force:
                skipped += 1
                continue

            try:
                req = Request(product.image_url, headers={"User-Agent": "Mozilla/5.0"})
                with urlopen(req, timeout=30) as resp:
                    content_type = resp.headers.get("Content-Type", "image/jpeg")
                    data = resp.read()
            except Exception as exc:  # noqa: BLE001 - report and continue
                failed += 1
                self.stderr.write(f"✗ {product.name}: {exc}")
                continue

            ext = mimetypes.guess_extension(content_type.split(";")[0].strip()) or ".jpg"
            if ext == ".jpe":
                ext = ".jpg"
            filename = f"{slugify(product.name)}{ext}"
            product.image.save(filename, ContentFile(data), save=True)
            downloaded += 1
            self.stdout.write(f"✓ {product.name} -> media/products/{filename}")
            time.sleep(0.2)  # be gentle with the image host

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Downloaded {downloaded}, skipped {skipped}, failed {failed}."
            )
        )
        self.stdout.write("Images are saved under the media/ folder.")
