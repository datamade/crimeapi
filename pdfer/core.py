from globalmaptiles import GlobalMercator
from tilenames import tileXY, tileEdges
# from PIL import Image, ImageEnhance
import cv2
import numpy as np
import cairo
import os
from helpers import dl_write_all, hex_to_rgb
from datetime import datetime
from shapely.geometry import box, Polygon, MultiPolygon, Point

mercator = GlobalMercator()

PAGE_SIZES = {
    'letter': (1275,1650,5,7,),
    'tabloid': (2550,3300,10,14,),
}

def pdfer(data, page_size='letter'):
    overlays = [l for l in data.get('overlays', [])]
    grid = {'zoom': data.get('zoom')}
    center_lon, center_lat = data['center']
    center_tile_x, center_tile_y = tileXY(float(center_lat), float(center_lon), int(data['zoom']))
    dim_across, dim_up = data['dimensions']
    if dim_across > dim_up:
        page_height, page_width, tiles_up, tiles_across = PAGE_SIZES[page_size]
        orientation = 'landscape'
    else:
        page_width, page_height, tiles_across, tiles_up = PAGE_SIZES[page_size]
        orientation = 'portrait'
    min_tile_x = center_tile_x - (tiles_across / 2)
    min_tile_y = center_tile_y - (tiles_up / 2)
    max_tile_x = min_tile_x + tiles_across
    max_tile_y = min_tile_y + tiles_up
    links = []
    for ty in range(min_tile_y, max_tile_y + 1):
        for tx in range(min_tile_x, max_tile_x + 1):
            links.append('http://a.tiles.mapbox.com/v3/datamade.hnmob3j3/{0}/{1}/{2}.png'.format(grid['zoom'], tx, ty))
    links = sorted(links)
    xcoord = 0
    ycoord = 0
    image_array = np.array()
    for link in links:
        parts = s.split('/')[-3:]
        parts[-1] = parts[-1].rstrip('.png')
        key = '-'.join(parts)
        grid[key] = {}
        grid[key]['bbox'] = tileEdges(float(parts[1]),float(parts[2]),int(parts[0]))
       #grid[key]['imagex'] = 256*xcoord
       #grid[key]['imagey'] = 256*ycoord
        ycoord += 1
        image_array.put(cv2.imread('/tmp/' + link))
        if ycoord > tiles_up:
            ycoord = 0
            xcoord = xcoord + 1
        if xcoord > tiles_across:
            xcoord = 0
            ycoord = ycoord + 1
    full_paths = dl_write_all(links)
    image = Image.new('RGBA', (page_width, page_height))
    path = '/tmp/'
    now = datetime.now()
    date_string = datetime.strftime(now, '%Y-%m-%d_%H-%M-%S')
    image_name = os.path.join('/tmp', '{0}.png'.format(date_string))
    for full_path in full_paths:
        try:
            tile = Image.open(full_path)
            parts = full_path.split('/')[-1].split('-')[-3:]
            key = '-'.join(parts).rstrip('.png')
            xcoord = grid[key]['imagex']
            ycoord = grid[key]['imagey']
            image.paste(tile, (xcoord, ycoord))
            image.save(image_name, 'PNG')
        except IOError:
            pass
    d = {}
    keys = sorted(grid.keys())
    if len(overlays):
        polys = []
        for k,v in grid.items():
            try:
                one,two,three,four = grid[k]['bbox']
                polys.append(box(two, one, four, three))
            except TypeError:
                pass
        mpoly = MultiPolygon(polys)
        bb_poly = box(*mpoly.bounds)
        min_key = keys[0]
        max_key = keys[-2]
        bminx, bminy = grid[min_key]['bbox'][0], grid[min_key]['bbox'][1]
        bmaxx, bmaxy = grid[max_key]['bbox'][2], grid[max_key]['bbox'][3]
        bmin_mx, bmin_my = mercator.LatLonToMeters(bminx, bminy)
        bmax_mx, bmax_my = mercator.LatLonToMeters(bmaxx, bmaxy)
        bmin_px, bmin_py = mercator.MetersToPixels(bmin_mx,bmin_my,float(grid['zoom']))
        bmax_px, bmax_py = mercator.MetersToPixels(bmax_mx,bmax_my,float(grid['zoom']))
        bmin_rx, bmin_ry = mercator.PixelsToRaster(bmin_px,bmin_py,int(grid['zoom']))
        im = cairo.ImageSurface.create_from_png(image_name)
        ctx = cairo.Context(im)
        for o in overlays:
            color = hex_to_rgb(o['color'])
            for p in o['points']:
                pt = Point((float(p[0]), float(p[1])))
                if bb_poly.contains(pt):
                    mx, my = mercator.LatLonToMeters(float(p[1]), float(p[0]))
                    px, py = mercator.MetersToPixels(mx,my,float(grid['zoom']))
                    rx, ry = mercator.PixelsToRaster(px,py,int(grid['zoom']))
                    nx, ny = int(rx - bmin_rx), int(ry - (bmin_ry - 256))
                    ctx.set_source_rgba(color[0]/255, color[1]/255, color[2]/255, 0.7)
                    ctx.arc(nx, ny, 10.0, 0, 50) # args: center-x, center-y, radius, ?, ?
                    ctx.fill()
                    ctx.arc(nx, ny, 10.0, 0, 50)
                    ctx.set_source_rgba(color[0]/255, color[1]/255, color[2]/255, 0.9)
                    ctx.stroke()
        im.write_to_png(image_name)
    scale = 1
    pdf_name = image_name.rstrip('.png') + '.pdf'
    pdf = cairo.PDFSurface(pdf_name, page_width, page_height)
    ctx = cairo.Context(pdf)
    image = cairo.ImageSurface.create_from_png(image_name)
   #if image.get_width() > width - 40:
   #    width_ratio = float(width - 40) // float(image.get_width())
   #    height_ratio = float(height - 40) // float(image.get_height())
   #    scale = min(height_ratio, width_ratio)
   #ctx.select_font_face('Sans')
   #title = 'CrimeAround.Us'
   #ctx.set_font_size(40)
   #t_width, t_height = ctx.text_extents(title)[2], ctx.text_extents(title)[3]
   #ctx.move_to((width//2) - (t_width//2),60)
   #ctx.show_text(title)
   #ctx.set_font_size(24)
   #date = datetime.strftime(now, '%B %d, %Y %I:%M%p')
   #d_width = ctx.text_extents(date)[2]
   #ctx.move_to((width//2) - (d_width//2), t_height + 70)
   #ctx.show_text(date)
   #ctx.set_font_size(24)
   #if len(overlays):
   #    ctx.move_to(20, image.get_height() + 220)
   #    ctx.show_text('Layers')
   #    ctx.set_font_size(18)
   #    ctx.move_to(20, image.get_height() + ctx.text_extents('Layers')[3] + 235)
   #    x,y = ctx.get_current_point()
   #    for o in overlays:
   #        ctx.move_to(x, y)
   #        color = hex_to_rgb(o['color'])
   #        ctx.set_source_rgba(color[0]/255, color[1]/255, color[2]/255, 1.0)
   #        ctx.arc(x+20, y, 15.0, 0, 50)
   #        ctx.fill()
   #        ctx.move_to(x + 50, y)
   #        ctx.show_text(o['name'])
   #        y = y + ctx.text_extents(o['name'])[3] + 25
   #ctx.scale(scale, scale)
    ctx.set_source_surface(image, 0, 0)
    ctx.paint()
    pdf.finish()
    return 'pdf saved %s' % (pdf_name)

if __name__ == "__main__":
    data = {'center': [-87.65137195587158, 41.8737151810189],
        'dimensions': [890, 600],
        'overlays': [{'color': '#ff0000',
             'points': [[-87.6426826613853, 41.8781071880535],
                 [-87.63938375754306, 41.867041706472456],
                 [-87.6545186129677, 41.865850595857054],
                 [-87.63909667701795, 41.86880452372822],
                 [-87.6393048378162, 41.86449456528135],
                 [-87.6393679750852, 41.867143148345015],
                 [-87.64741565794833, 41.87881063893845],
                 [-87.65197660167782, 41.87670825544318],
                 [-87.63909667701795, 41.86880452372822],
                 [-87.65620174057511, 41.86603890823199],
                 [-87.65714742488014, 41.866878732430045],
                 [-87.66390400959368, 41.86815871640521],
                 [-87.65196361130707, 41.874474361734165],
                 [-87.63909667701795, 41.86880452372822],
                 [-87.65696499902725, 41.874432576058304],
                 [-87.65685596043203, 41.876416024306245],
                 [-87.64395748847578, 41.87189638577255],
                 [-87.6548116345001, 41.8777184577741],
                 [-87.65934485800273, 41.86599153498752],
                 [-87.65924273143733, 41.86592781781541]]}],
        'zoom': 15}
    print pdfer(data, page_size='tabloid')
