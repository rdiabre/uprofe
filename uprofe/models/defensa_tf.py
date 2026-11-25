# -*- coding: utf-8 -*-
import re

from odoo import models, fields, api

MAX_NUM_DEFENSA = 20
#letras mayúsculas, números y guiones, sin espacios. Ej: DEF-2026-001
REGEX_NUM_DEFENSA = r'^[A-Z0-9-]+$'
PRIMER_ANIO = 2000 
NOTA_MIN = 0.0
NOTA_MAX = 10.0


class DefensaTF(models.Model):
    _name = 'uprofe.defensa_tf'
    _description = 'UPROFE Defensa de trabajo final'
    _rec_name = 'sNum_defensa'
    _order = 'dFecha desc, fHora asc'

    sNum_defensa = fields.Char(string="Nº de defensa", size=MAX_NUM_DEFENSA, required=True, copy=False, help="Identificador de la defensa. Ejemplo: DEF-2026-001") 
    dFecha = fields.Date(string="Fecha", required=True, default=fields.Date.context_today)
    fHora = fields.Float(string="Hora", required=True, help="Hora de inicio. Ejemplo: 9:30")
    #opcional, la nota no existe hasta que no se celebra la defensa. Por defecto está en 0.
    fCalificacion = fields.Float(string="Calificación", default=0.0, help="Nota del 0 al 10 de la defensa")

    #cada defensa es de un solo trabajo y cada trabajo tiene como mucho una defensa
    trabajo_final_id = fields.Many2one('uprofe.trabajo_final', string="Trabajo final", required=True, ondelete='restrict')

    #cada defensa la juzga un solo tribunal y un tribunal juzga varias
    tribunal_tf_id = fields.Many2one('uprofe.tribunal_tf', string="Tribunal", required=True, ondelete='restrict')

    #cada defensa se hace en un espacio y un espacio puede acoger varias
    espacio_id = fields.Many2one('uprofe.espacio', string="Espacio", required=True, ondelete='restrict')

    #alumno de la defensa, sacado de su trabajo final; para filtrar por él
    alumno_id = fields.Many2one(related='trabajo_final_id.alumno_id', string="Alumno", store=True)

    _sql_constraints = [
        #impide que dos defensas tengan el mismo número
        ('num_defensa_unique', 'unique("sNum_defensa")', 'Ya existe una defensa con este número.'),
        #un trabajo final solo se defiende una vez
        ('trabajo_final_unique', 'unique(trabajo_final_id)', 'Este trabajo final ya tiene una defensa.'),
        #un tribunal no puede juzgar dos defensas a la vez
        ('tribunal_fecha_hora_unique', 'unique(tribunal_tf_id, "dFecha", "fHora")',
         'Este tribunal ya tiene otra defensa a esa fecha y hora.'),
        #en un espacio no puede haber dos defensas a la vez
        ('espacio_fecha_hora_unique', 'unique(espacio_id, "dFecha", "fHora")',
         'Ese espacio ya está ocupado por otra defensa a esa fecha y hora.'),
    ]

    #nombre que se muestra en los desplegables de otros modelos: "DEF-2026-001 · TF-2026-001"
    #me la ha hecho la IA
    @api.depends('sNum_defensa', 'trabajo_final_id.sNum_tf')
    def _compute_display_name(self):
        for record in self:
            if record.sNum_defensa and record.trabajo_final_id:
                record.display_name = f"{record.sNum_defensa} · {record.trabajo_final_id.sNum_tf or ''}"
            else:  #si falta algo (registro nuevo), se muestra lo que haya
                record.display_name = record.sNum_defensa or ''

    #número: no vacío, máximo de caracteres y solo mayúsculas, números y guiones
    @api.constrains('sNum_defensa')
    def _check_num_defensa(self):
        for record in self:
            numero = (record.sNum_defensa or '').strip()
            if not numero:
                raise models.ValidationError("El número de la defensa no puede estar vacío.")
            if len(numero) > MAX_NUM_DEFENSA:
                raise models.ValidationError(f"El número no puede tener más de {MAX_NUM_DEFENSA} caracteres.")
            if not re.match(REGEX_NUM_DEFENSA, numero):
                raise models.ValidationError("El número solo puede contener letras mayúsculas, números y guiones, sin espacios.")

    #la fecha no puede ser anterior al año 2000, sí pueden ser futuras porque se reservan con mucho tiempo de antelación
    @api.constrains('dFecha')
    def _check_fecha(self):
        for record in self:
            if record.dFecha and record.dFecha.year < PRIMER_ANIO:
                raise models.ValidationError(f"La fecha de la defensa no puede ser anterior a {PRIMER_ANIO}.")

    #hora entre las 0:00 y las 24:00
    @api.constrains('fHora')
    def _check_hora(self):
        for record in self:
            if not 0 <= record.fHora < 24:
                raise models.ValidationError("La hora debe estar entre las 0:00 y las 23:59.")

    #nota entre 0 y 10
    @api.constrains('fCalificacion')
    def _check_calificacion(self):
        for record in self:
            if not NOTA_MIN <= record.fCalificacion <= NOTA_MAX:
                raise models.ValidationError(f"La calificación debe estar entre {NOTA_MIN:g} y {NOTA_MAX:g}.")

    #regla entre dos campos: no se puede poner nota a una defensa que todavía no se ha celebrado.
    #(se incluye dFecha para que salte también al cambiar la fecha de una defensa que ya tenía nota)
    @api.constrains('fCalificacion', 'dFecha')
    def _check_calificacion_vs_fecha(self):
        hoy = fields.Date.context_today(self)
        for record in self:
            if record.fCalificacion and record.dFecha and record.dFecha > hoy:
                raise models.ValidationError("No se puede calificar una defensa que todavía no se ha celebrado.")

    #número en mayúsculas y sin espacios
    @api.onchange('sNum_defensa')
    def _onchange_num_defensa(self):
        if self.sNum_defensa:
            self.sNum_defensa = self.sNum_defensa.replace(' ', '').upper()