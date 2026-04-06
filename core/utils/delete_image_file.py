from __future__ import annotations

from typing import Optional

from django.core.files.storage import default_storage


def delete_image_file(field_file: Optional[object]) -> None:
	"""Elimina un archivo de imagen asociado a un ImageField si existe."""
	if not field_file:
		return

	file_name = getattr(field_file, "name", None)
	if not file_name:
		return

	if default_storage.exists(file_name):
		default_storage.delete(file_name)
