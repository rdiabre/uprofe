# -*- coding: utf-8 -*-
import re

from odoo import models, fields, api

MAX_NUM_TRIBUNAL = 20
#letras mayúsculas, números y guiones, sin espacios. Ej: TRIB-2026-01
REGEX_NUM_TRIBUNAL = r'^[A-Z0-9-]+$'
MIN_PROFESORES = 3   #un tribunal tiene de 3 a N profesores
PRIMER_ANIO = 2000   #para evitar erratas en los años


class TribunalTF(models.Model):
    _name = 'uprofe.tribunal_tf'
    _description = 'UPROFE Tribunal de trabajo final'
    _rec_name = 'sNum_tribunal'
    _order = 'dFecha_constitucion desc, sNum_tribunal asc'

    #clave primaria
    sNum_tribunal = fields.Char(string="Nº de tribunal", size=MAX_NUM_TRIBUNAL, required=True, copy=False, help="Identificador del tribunal. Ejemplo: TRIB-2026-01") 
    dFecha_constitucion = fields.Date(string="Fecha de constitución", required=True, default=fields.Date.context_today)

    #un tribunal tiene como mínimo 3 profesores y un profesor puede estar en 0 o muchos tribunales.
    profesor_ids = fields.Many2many('uprofe.profesor', string="Profesores")

    #puede no haber ningún investigador en el tribunal
    investigador_ids = fields.Many2many('uprofe.investigador', string="Investigadores")

    #un tribunal defiende una o muchas defensas y cada defensa tiene un solo tribunal
    defensa_tf_ids = fields.One2many('uprofe.defensa_tf', 'tribunal_tf_id', string="Defensas")

    iNum_miembros = fields.Integer(string="Nº de miembros", compute='_compute_num_miembros')

    _sql_constraints = [
        #impide que dos tribunales tengan el mismo número
        ('num_tribunal_unique', 'unique("sNum_tribunal")', 'Ya existe un tribunal con este número.'),
    ]

    @api.depends('profesor_ids', 'investigador_ids')
    def _compute_num_miembros(self):
        for record in self:
            record.iNum_miembros = len(record.profesor_ids) + len(record.investigador_ids)

    #número: no vacío, máximo de caracteres y solo mayúsculas, números y guiones
    @api.constrains('sNum_tribunal')
    def _check_num_tribunal(self):
        for record in self:
            numero = (record.sNum_tribunal or '').strip()
            if not numero:
                raise models.ValidationError("El número del tribunal no puede estar vacío.")
            if len(numero) > MAX_NUM_TRIBUNAL:
                raise models.ValidationError(f"El número no puede tener más de {MAX_NUM_TRIBUNAL} caracteres.")
            if not re.match(REGEX_NUM_TRIBUNAL, numero):
                raise models.ValidationError("El número solo puede contener letras mayúsculas, números y guiones, sin espacios.")

    @api.constrains('dFecha_constitucion')
    def _check_fecha_constitucion(self):
        hoy = fields.Date.context_today(self)
        for record in self:
            if record.dFecha_constitucion and record.dFecha_constitucion.year < PRIMER_ANIO:
                raise models.ValidationError(f"La fecha de constitución no puede ser anterior a {PRIMER_ANIO}.")
            if record.dFecha_constitucion and record.dFecha_constitucion > hoy:
                raise models.ValidationError("La fecha de constitución no puede ser posterior a la actual")

    #mínimo de profesores (3,N). Incluyo también sNum_tirbunal para que salte la validacion al crear un tribunal sin profesores
    @api.constrains('profesor_ids', 'sNum_tribunal')
    def _check_min_profesores(self):
        for record in self:
            if len(record.profesor_ids) < MIN_PROFESORES:
                raise models.ValidationError(f"Un tribunal debe tener al menos {MIN_PROFESORES} profesores.")

    #número en mayúsculas y sin espacios
    @api.onchange('sNum_tribunal')
    def _onchange_num_tribunal(self):
        if self.sNum_tribunal:
            self.sNum_tribunal = self.sNum_tribunal.replace(' ', '').upper()