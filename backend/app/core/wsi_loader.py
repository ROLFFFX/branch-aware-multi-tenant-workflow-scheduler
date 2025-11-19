import openslide
from pathlib import Path

class WSILoader:
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.slide = openslide.OpenSlide(str(self.file_path))

    def metadata(self):
        return {
            "width": self.slide.dimensions[0],
            "height": self.slide.dimensions[1],
            "levels": self.slide.level_count,
            "level_dimensions": self.slide.level_dimensions,
            "level_downsamples": self.slide.level_downsamples
        }

    def read_region(self, x, y, level, size):
        """
        Reads a tile at specified location.
        Returns a PIL Image.
        """
        return self.slide.read_region((x, y), level, (size, size)).convert("RGB")

    def get_lowres_image(self, level=None):
        """
        Get an entire low-resolution image 
        for tissue mask generation.
        """
        if level is None:
            # pick last level by default (lowest resolution)
            level = self.slide.level_count - 1
        
        return self.read_region(0, 0, level, self.slide.level_dimensions[level][0])
