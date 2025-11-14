
import os
import uuid
import traceback
from typing import Optional, Tuple
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont

try:
    from celery import shared_task  # type: ignore[import]
except ImportError:  # pragma: no cover
    def shared_task(*args, **kwargs):  # type: ignore[misc]
        def decorator(func):
            return func

        return decorator

# مسیرهای ثابت
ASSETS_DIR = os.path.join(settings.BASE_DIR, 'assets')
SHIRT_DIR = os.path.join(ASSETS_DIR, 'shirts')
FONT_DIR = os.path.join(ASSETS_DIR, 'fonts')
MEDIA_MOCKUP_DIR = os.path.join(settings.MEDIA_ROOT, 'mockups')

SHIRT_FILE_MAP = {
    'white': 'white.png',
    'black': 'black.png',
    'blue': 'blu.jpg',
    'yellow': 'yellow.png',
}

DEFAULT_SHIRT_COLORS = list(SHIRT_FILE_MAP.keys())

print("=== TASKS MODULE IMPORTED ===")


def _coerce_uuid(value: str) -> Optional[uuid.UUID]:
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def _resolve_shirt_asset(color: str) -> Optional[str]:
    """Return the path to the requested shirt color asset, if available."""
    normalized = (color or '').lower().strip()
    if not normalized:
        return None

    filename = SHIRT_FILE_MAP.get(normalized)
    if filename:
        candidate = os.path.join(SHIRT_DIR, filename)
        if os.path.exists(candidate):
            return candidate

    # Fallback: direct filename match with any extension
    for ext in ('.png', '.jpg', '.jpeg'):
        candidate = os.path.join(SHIRT_DIR, f"{normalized}{ext}")
        if os.path.exists(candidate):
            return candidate

    return None


def _prepare_shirt_image(color: str) -> Optional[Image.Image]:
    asset_path = _resolve_shirt_asset(color)
    if asset_path is None:
        print(f"No asset found for color '{color}' in {SHIRT_DIR}")
        return None

    with Image.open(asset_path).convert("RGBA") as src:
        return src.copy()


def _remove_mockup(mockup) -> None:
    if not mockup:
        return

    try:
        images = list(mockup.images.all())
        for generated in images:
            try:
                generated.image.delete(save=False)
            except Exception:
                image_path = getattr(generated.image, 'path', None)
                if image_path and os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                    except OSError:
                        traceback.print_exc()
            generated.delete()
        mockup.delete()
    except Exception:
        traceback.print_exc()


def _darken_color(color_hex: str, factor: float = 0.4) -> str:
    """Darken a hex color by a factor (0.0 = black, 1.0 = original)."""
    try:
        color_hex = color_hex.strip().lstrip('#')
        if len(color_hex) == 3:
            color_hex = ''.join([c*2 for c in color_hex])
        r = int(color_hex[0:2], 16)
        g = int(color_hex[2:4], 16)
        b = int(color_hex[4:6], 16)
        r = max(0, min(255, int(r * factor)))
        g = max(0, min(255, int(g * factor)))
        b = max(0, min(255, int(b * factor)))
        return f"#{r:02x}{g:02x}{b:02x}"
    except:
        return '#000000'


def _determine_text_and_outline(shirt_color: str, requested_text_color: Optional[str]) -> Tuple[str, str, str]:
    """Determine optimal text, shadow, and outline colors for readability.
    Returns: (text_color, shadow_color, outline_color)
    """
    normalized = (shirt_color or '').lower()

    color = (requested_text_color or '').strip()
    if not color:
        color = '#000000'

    # For blue shirts - use bright white text if user didn't specify, otherwise use their color
    if normalized == 'blue':
        if color.upper() == '#000000':
            color = '#FFFFFF'  # Default to white on blue
        shadow_color = _darken_color(color, 0.3)  # Dark shadow
        outline_color = '#000000'  # Black outline for contrast
    
    # For yellow/orange shirts - use black text if user didn't specify, otherwise use their color
    elif normalized == 'yellow':
        if color.upper() == '#FFFFFF' or color.upper() == '#FFF':
            color = '#000000'  # Default to black on yellow
        shadow_color = _darken_color(color, 0.5)  # Darker shadow
        outline_color = '#000000'  # Black outline for contrast
    
    # For dark shirts (black), use white text if user didn't specify
    elif normalized == 'black':
        if color.upper() == '#000000':
            color = '#FFFFFF'
        shadow_color = _darken_color(color, 0.3)
        outline_color = '#000000' if color.upper() == '#FFFFFF' else '#FFFFFF'
    
    # For light shirts (white), use black text if user didn't specify
    elif normalized == 'white':
        if color.upper() == '#FFFFFF' or color.upper() == '#FFF':
            color = '#000000'
        shadow_color = _darken_color(color, 0.5)
        outline_color = '#FFFFFF' if color.upper() == '#000000' else '#000000'
    
    # Default: use requested color with appropriate shadow and outline
    else:
        shadow_color = _darken_color(color, 0.4)
        if color.upper() == '#FFFFFF' or color.upper() == '#FFF':
            outline_color = '#000000'
        else:
            outline_color = '#000000'  # Black outline works on most backgrounds
    
    return color, shadow_color, outline_color


def _get_font(font_name=None, size=48):
    """بارگذاری فونت امن"""
    try:
        if font_name:
            font_path = os.path.join(FONT_DIR, f"{font_name}.ttf")
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, size=size)
    except Exception as e:
        print("Font load failed:", e)
    return ImageFont.load_default()


@shared_task(bind=True)
def generate_mockup_task(self, generation_task_id, text, font_name=None, text_color="#000000", shirt_colors=None):
    from .models import Mockup, GeneratedImage, GenerationTask

    print(f"=== GENERATE MOCKUP STARTED for task {generation_task_id} ===")

    task_record = None
    task_uuid = _coerce_uuid(generation_task_id)
    if task_uuid:
        task_record, _ = GenerationTask.objects.get_or_create(task_id=task_uuid)
        if task_record.mockup_id:
            _remove_mockup(task_record.mockup)
            task_record.mockup = None
        task_record.status = 'STARTED'
        task_record.save(update_fields=['status', 'mockup', 'updated_at'])
    else:
        for previous in Mockup.objects.filter(text=text):
            _remove_mockup(previous)

    # Default colors
    if shirt_colors is None:
        shirt_colors = DEFAULT_SHIRT_COLORS

    # ایجاد دایرکتوری امن
    os.makedirs(MEDIA_MOCKUP_DIR, exist_ok=True)

    # ایجاد رکورد Mockup
    render_text_color, _, _ = _determine_text_and_outline(shirt_colors[0] if shirt_colors else 'white', text_color)

    mockup = Mockup.objects.create(
        text=text,
        font=font_name,
        text_color=render_text_color,
        shirt_color=",".join(shirt_colors) if shirt_colors else ""
    )

    results = []
    try:
        for color in shirt_colors[:4]:  # حداکثر 4 رنگ
            base = _prepare_shirt_image(color)
            if base is None:
                print(f"No base asset available for color '{color}', skipping.")
                continue

            draw = ImageDraw.Draw(base)
            img_w, img_h = base.size

            # Double the font size to 30% of image height for much better visibility
            font = _get_font(font_name, size=int(img_h * 0.30))
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            # Center horizontally, but position higher (at 35% from top instead of 50%)
            x = (img_w - text_w) / 2
            y = img_h * 0.35 - text_h / 2

            render_text_color, shadow_color, outline_color = _determine_text_and_outline(color, text_color)
            
            # Create 3D shadow effect: draw shadow offset down and to the right
            shadow_offset_x = 4
            shadow_offset_y = 4
            draw.text((x + shadow_offset_x, y + shadow_offset_y), text, font=font, fill=shadow_color)
            
            # Draw thick outline around the main text for definition
            outline_thickness = 3
            for ox in range(-outline_thickness, outline_thickness + 1):
                for oy in range(-outline_thickness, outline_thickness + 1):
                    if ox != 0 or oy != 0:  # Skip the center position
                        draw.text((x+ox, y+oy), text, font=font, fill=outline_color)
            
            # Draw main text on top for the 3D raised effect
            draw.text((x, y), text, font=font, fill=render_text_color)

            # ذخیره امن فایل
            out_name = f"mockup_{mockup.id}{color}{uuid.uuid4().hex[:8]}.png"
            out_path = os.path.join(MEDIA_MOCKUP_DIR, out_name)
            try:
                base.convert("RGB").save(out_path, "PNG")
            except PermissionError:
                print(f"Permission denied saving {out_path}, skipping.")
                continue
            except Exception as e:
                print(f"Failed to save {out_path}: {e}")
                continue

            # ایجاد رکورد مدل
            rel_path = os.path.join('mockups', out_name)
            gen_img = GeneratedImage.objects.create(mockup=mockup, image=rel_path)
            results.append({'image_url': gen_img.image.url, 'created_at': gen_img.created_at.isoformat()})
    except Exception as exc:
        traceback.print_exc()
        if task_record:
            task_record.status = 'FAILURE'
            task_record.save(update_fields=['status', 'updated_at'])
        raise exc
    else:
        if task_record:
            task_record.mockup = mockup
            task_record.status = 'SUCCESS'
            task_record.save(update_fields=['status', 'mockup', 'updated_at'])

    print(f"=== GENERATE MOCKUP FINISHED for task {generation_task_id} ===")
    return results