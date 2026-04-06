from __future__ import annotations

from io import BytesIO
from typing import Optional

from django.core.files.base import ContentFile


def compress_image(
	uploaded_file,
	max_size_kb: int = 100,
	initial_quality: int = 85,
	min_quality: int = 10,
	max_width: int = 2048,
	max_height: int = 2048,
	min_size_px: int = 64,
	quality_step: int = 5,
	scale_step: float = 0.75,
	max_iterations: int = 60,
) -> ContentFile:
	"""
	Comprime/redimensiona hasta dejar la imagen ≤ `max_size_kb` (100 KB por defecto).
	Estrategia: bajar calidad en pasos; si no alcanza, reducir dimensiones (75%) y reiniciar calidad.
	Usa JPEG progresivo y subsampling para mayor compresión. Falla si supera `max_iterations` o si
	las dimensiones quedarían por debajo de `min_size_px`.
	"""
	try:
		from PIL import Image, ImageOps
	except Exception:
		return uploaded_file

	max_size_bytes = max_size_kb * 1024

	image = Image.open(uploaded_file)
	try:
		image = ImageOps.exif_transpose(image)
	except Exception:
		pass
	if image.mode in ("RGBA", "LA"):
		image = image.convert("RGB")

	# Reducción inicial para evitar explosión de memoria
	if image.width > max_width or image.height > max_height:
		image.thumbnail((max_width, max_height), Image.LANCZOS)

	def save_to_buffer(img, q) -> BytesIO:
		buf = BytesIO()
		img.save(
			buf,
			format="JPEG",
			optimize=True,
			quality=q,
			progressive=True,
			subsampling=1,  # 4:2:0
		)
		return buf

	current_quality = initial_quality
	buffer = save_to_buffer(image, current_quality)
	iterations = 0

	while buffer.tell() > max_size_bytes:
		iterations += 1
		if iterations > max_iterations:
			raise ValueError(
				f"No se pudo comprimir la imagen por debajo de {max_size_kb} KB tras {max_iterations} intentos"
			)

		# Primero bajar calidad
		if current_quality > min_quality:
			current_quality = max(min_quality, current_quality - quality_step)
			buffer = save_to_buffer(image, current_quality)
			continue

		# Luego bajar dimensiones
		new_w = int(image.width * scale_step)
		new_h = int(image.height * scale_step)
		if new_w < min_size_px or new_h < min_size_px:
			raise ValueError("La imagen no pudo reducirse al tamaño requerido sin quedar demasiado pequeña")
		image = image.resize((new_w, new_h), Image.LANCZOS)
		current_quality = initial_quality
		buffer = save_to_buffer(image, current_quality)

	file_name = getattr(uploaded_file, "name", None) or "imagen.jpg"
	return ContentFile(buffer.getvalue(), name=file_name)
