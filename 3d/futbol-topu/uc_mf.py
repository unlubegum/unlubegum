"""Çok nesneli, çok parçalı 3MF yazıcı.

Her nesne dilimleyicide ayrı seçilebilir; nesnenin içindeki parçalar (beyaz/siyah)
ayrı "parça" olarak gelir ve filament (ekstrüder) ataması dosyada hazırdır.
PrusaSlicer biçimindeki Metadata/Slic3r_PE_model.config kullanılır; OrcaSlicer,
Snapmaker Orca, Bambu Studio ve PrusaSlicer bunu okur.
"""
import zipfile
import numpy as np
from xml.sax.saxutils import escape

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
 <Default Extension="config" ContentType="text/xml"/>
</Types>"""
RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>"""


def write_3mf(path, objects):
    """objects: [(ad, [(parça_adı, trimesh, ekstrüder), ...], (x, y)), ...]"""
    model = ['<?xml version="1.0" encoding="UTF-8"?>\n'
             '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
             'xmlns:slic3rpe="http://schemas.slic3r.org/3mf/2017/06">\n'
             ' <metadata name="slic3rpe:Version3mf">1</metadata>\n <resources>\n']
    config = ['<?xml version="1.0" encoding="UTF-8"?>\n<config>\n']
    items = []
    for oid, (name, parts, (x, y)) in enumerate(objects, start=1):
        # Nesneyi kendi merkezine al, tablaya item dönüşümüyle yerleştir
        allv = np.vstack([m.vertices for _, m, _ in parts])
        c = (allv.min(0) + allv.max(0)) / 2
        c[2] = allv[:, 2].min()
        vs, ts, vols, voff, toff = [], [], [], 0, 0
        for pname, m, ext in parts:
            vs.append(m.vertices - c)
            ts.append(m.faces + voff)
            vols.append((pname, ext, toff, toff + len(m.faces) - 1))
            voff += len(m.vertices); toff += len(m.faces)
        V, T = np.vstack(vs), np.vstack(ts)
        model.append(f'  <object id="{oid}" type="model">\n   <mesh>\n    <vertices>\n')
        model.append("".join(f'     <vertex x="{a:.4f}" y="{b:.4f}" z="{d:.4f}"/>\n' for a, b, d in V))
        model.append('    </vertices>\n    <triangles>\n')
        model.append("".join(f'     <triangle v1="{a}" v2="{b}" v3="{d}"/>\n' for a, b, d in T))
        model.append('    </triangles>\n   </mesh>\n  </object>\n')
        items.append(f'  <item objectid="{oid}" transform="1 0 0 0 1 0 0 0 1 {x:.3f} {y:.3f} 0" printable="1"/>\n')
        config.append(f' <object id="{oid}" instances_count="1">\n'
                      f'  <metadata type="object" key="name" value="{escape(name)}"/>\n')
        for pname, ext, a, b in vols:
            config.append(f'  <volume firstid="{a}" lastid="{b}">\n'
                          f'   <metadata type="volume" key="name" value="{escape(pname)}"/>\n'
                          f'   <metadata type="volume" key="volume_type" value="ModelPart"/>\n'
                          f'   <metadata type="volume" key="extruder" value="{ext}"/>\n'
                          f'   <metadata type="volume" key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>\n'
                          f'   <metadata type="volume" key="source_object_id" value="{oid - 1}"/>\n'
                          f'  </volume>\n')
        config.append(' </object>\n')
    model.append(' </resources>\n <build>\n' + "".join(items) + ' </build>\n</model>\n')
    config.append('</config>\n')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("3D/3dmodel.model", "".join(model))
        z.writestr("Metadata/Slic3r_PE_model.config", "".join(config))
