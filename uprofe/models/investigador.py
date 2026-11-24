# -*- coding: utf-8 -*-
import re

from odoo import models, fields, api

MAX_AREA = 100
#ORCID: Estaba en el diagrama y se lo he pedido a la IA --> 4 bloques de 4 cifras separados por guiones; la última puede ser una X. Ej: 0000-0002-1825-0097
REGEX_ORCID = r'^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$' 
#Otros roles de persona con los que Investigador es excluyente. Creo que hay que mirar el diagrama, porque un profesor puede ser investigador, pero el diagrama dice que no 
#si finalmente un profesor puede ser investigador también, quitar la línea correspondiente de esta lista
OTROS_ROLES = [
    ('uprofe.alumno', 'alumno'),
    ('uprofe.profesor', 'profesor'),
    ('uprofe.tutor_externo', 'tutor externo'),
]


class Investigador(models.Model):
    _name = 'uprofe.investigador'
    _description = 'Investigador'
    _order = 'sApellidos asc, name asc'

    #Herencia por delegación, como profesor y alumno, #losInvestigadoresTambiénSonPersonas
    _inherits = {'uprofe.persona': 'persona_id'}

    persona_id = fields.Many2one('uprofe.persona', string="Persona", required=True, ondelete='cascade')
    #usuario_id = fields.Many2one('uprofe.usuario', string="Usuario", required=True, ondelete='restrict')

    #son opcionales porque así figura en el diagrama
    sOrcid = fields.Char(string="ORCID", size=19, copy=False, help="Identificador ORCID. Ejemplo: 0000-0002-1825-0097")
    sArea_investigacion = fields.Char(string="Área de investigación")

    #un investigador trabaja sobre n investigaciones. no se puede tener un investigador sin lineas
    linea_investigacion_ids = fields.Many2many('uprofe.linea_investigacion', string="Lineas de investigación")
    #un investigador puede publicar pila de publicaciones o ninguna
    publicacion_ids = fields.Many2many('uprofe.publicacion', string="Publicaciones")

    #un investigador puede pertenecer a muchos o a ningún tribunal, lo descomentaré cuando haga tribunal
    #tribunal_tf_ids = fields.Many2many('uprofe.tribunal_tf', string="Tribunales")

    iNum_publicaciones = fields.Integer(string="Nº de publicaciones", compute='_compute_totales')
    iNum_lineas = fields.Integer(string="Nº de líneas de investigación", compute='_compute_totales')

    _sql_constraints = [
        ('persona_unique', 'unique(persona_id)', 'Esta persona ya está registrada como investigador.'),
        ('orcid_unique', 'unique("sOrcid")', 'Ya existe un investigador con este ORCID.'), #el orcid no se puede repetir, no tendría sentido
        #('usuario_unique', 'unique(usuario_id)', 'Este usuario ya está asociado a otro investigador.')
    ]

    @api.depends('publicacion_ids', 'linea_investigacion_ids')
    def _compute_totales(self):
        for record in self:
            record.iNum_publicaciones = len(record.publicacion_ids)
            record.iNum_lineas = len(record.linea_investigacion_ids)

    #Una persona es alumno, profesor, investigador o tutor externo, nunca dos a la vez (igual que en Alumno).
    #Los roles cuyo modelo todavía no existe se saltan, y así este modelo funciona solo y no da KeyError.
    @api.constrains('persona_id')
    def _check_no_es_otra_persona(self):
        for record in self:
            for modelo, rol in OTROS_ROLES: #tengo que decir que esto de la lista ha sido idea de la IA
                if modelo in self.env and 'persona_id' in self.env[modelo]._fields and self.env[modelo].search_count([('persona_id', '=', record.persona_id.id)]):
                    raise models.ValidationError(f"Esta persona ya está registrada como {rol}.")

    #es un atributo opcional, pero si se rellena debe tener el formato correcto y un dígito de control válido
    @api.constrains('sOrcid')
    def _check_orcid(self):
        for record in self:
            if not record.sOrcid:
                continue
            orcid = record.sOrcid.strip()
            if not re.match(REGEX_ORCID, orcid):
                raise models.ValidationError("El ORCID debe tener el formato 0000-0000-0000-0000.")
            if not self._orcid_valido(orcid):
                raise models.ValidationError("El ORCID no es válido: el último dígito de control no coincide.")

    #lo mismo, es opcional, pero aquí hacemos las cosas bien
    @api.constrains('sArea_investigacion')
    def _check_area(self):
        for record in self:
            if record.sArea_investigacion:
                area = record.sArea_investigacion.strip()
                if not area:
                    raise models.ValidationError("El área de investigación no puede estar vacía.")
                if len(area) > MAX_AREA:
                    raise models.ValidationError(f"El área de investigación no puede tener más de {MAX_AREA} caracteres.")

    #esto es un consejo de Claude, no sé qué habla del ISO ni de nada pero no me vas a tumbar el modelo Aurelio
    #Comprueba el último dígito del ORCID (norma ISO 7064 módulo 11-2, la que usa ORCID)
    @api.model
    def _orcid_valido(self, orcid):
        digitos = orcid.replace('-', '')
        total = 0
        for digito in digitos[:15]:
            total = (total + int(digito)) * 2
        resultado = (12 - total % 11) % 11
        control = 'X' if resultado == 10 else str(resultado)
        return digitos[15] == control

    #orcid sin espacios, con X mayúscula y con guiones: "0000000218250097" -> "0000-0002-1825-0097"
    @api.onchange('sOrcid')
    def _onchange_orcid(self):
        if self.sOrcid:
            orcid = self.sOrcid.replace(' ', '').upper()
            if re.match(r'^\d{15}[\dX]$', orcid):
                orcid = f"{orcid[0:4]}-{orcid[4:8]}-{orcid[8:12]}-{orcid[12:16]}"
            self.sOrcid = orcid

    #área sin espacios sobrantes y con la primera letra en mayúscula, el resto queda igual
    @api.onchange('sArea_investigacion')
    def _onchange_area(self):
        if self.sArea_investigacion:
            area = self.sArea_investigacion.strip()
            self.sArea_investigacion = area[:1].upper() + area[1:]