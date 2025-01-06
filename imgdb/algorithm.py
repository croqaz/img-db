from collections import Counter

from PIL import Image

from .config import g_config
from .util import rgb_to_hex

# import torch
# from transformers import BeitFeatureExtractor, BeitForImageClassification
# from transformers import AutoFeatureExtractor, DeiTForImageClassificationWithTeacher
# beit_feature_extractor = BeitFeatureExtractor.from_pretrained('microsoft/beit-base-patch16-224-pt22k-ft22k')
# beit_model = BeitForImageClassification.from_pretrained('microsoft/beit-base-patch16-224-pt22k-ft22k')
# deit_feature_extractor = AutoFeatureExtractor.from_pretrained('facebook/deit-base-distilled-patch16-224')
# deit_model = DeiTForImageClassificationWithTeacher.from_pretrained('facebook/deit-base-distilled-patch16-224')
# yolov5_model = torch.hub.load('ultralytics/yolov5', 'yolov5x')


def top_colors(img: Image.Image, cut=g_config.top_color_cut):
    SZ = 256
    img = img.convert('RGB')
    if img.width > SZ or img.height > SZ:
        img.thumbnail((SZ, SZ))
    collect_colors = []
    for x in range(img.width):
        for y in range(img.height):
            collect_colors.append(closest_color(img.getpixel((x, y))))
    total = len(collect_colors)
    # stat = {k: round(v / total * 100, 1) for k, v in Counter(collect_colors).items() if v / total * 100 >= cut}
    # log.info(f'Collected {len(set(collect_colors)):,} uniq colors, cut to {len(stat):,} colors')
    return [f'{k[-1]}={round(v/total*100, 1)}' for k, v in Counter(collect_colors).items() if v / total * 100 >= cut]


def closest_color(pair: tuple, split=g_config.top_clr_round_to):
    r, g, b = pair
    r = round(r / split) * split
    g = round(g / split) * split
    b = round(b / split) * split
    if r > 250:
        r = 255
    if g > 250:
        g = 255
    if b > 250:
        b = 255
    return r, g, b, rgb_to_hex((r, g, b))


# def obj_detect_yolov5(img: Image.Image):
#     results = yolov5_model(img)
#     results.print()
#     return sorted(set(n for n in results.pandas().xyxy[0]['name']))


ALGORITHMS = {
    'top-colors': top_colors,
    # 'obj-detect-yolov5': obj_detect_yolov5,
}
