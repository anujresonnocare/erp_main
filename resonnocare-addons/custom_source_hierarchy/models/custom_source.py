from odoo import fields, models, api
from odoo.exceptions import ValidationError


class CustomSource(models.Model):
    _name = 'custom.source'
    _description = 'Custom Source with Hierarchy'
    _parent_store = True
    _parent_name = 'parent_id'
    _order = 'parent_path, name'

    name = fields.Char(
        string='Name',
        required=True,
        translate=True
    )
    
    code = fields.Char(
        string='Code',
        required=True,
        help='Unique identifier for this source'
    )
    
    description = fields.Text(
        string='Description',
        translate=True
    )
    
    parent_id = fields.Many2one(
        'custom.source',
        string='Parent Source',
        index=True,
        ondelete='cascade',
        help='Parent source in the hierarchy'
    )
    
    child_ids = fields.One2many(
        'custom.source',
        'parent_id',
        string='Child Sources',
        help='Children of this source'
    )
    
    parent_path = fields.Char(
        string='Parent Path',
        index=True,
        help='Hierarchical path for fast queries'
    )
    
    children_count = fields.Integer(
        string='Number of Children',
        compute='_compute_children_count',
        store=True
    )
    
    level = fields.Integer(
        string='Level in Hierarchy',
        compute='_compute_level',
        store=True
    )
    
    is_root = fields.Boolean(
        string='Is Root',
        compute='_compute_is_root',
        store=True
    )
    
    full_path = fields.Char(
        string='Full Path',
        compute='_compute_full_path',
        store=False,
        help='Full hierarchy path'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    @api.depends('child_ids')
    def _compute_children_count(self):
        for record in self:
            record.children_count = len(record.child_ids)
    
    @api.depends('parent_id')
    def _compute_level(self):
        for record in self:
            level = 0
            parent = record.parent_id
            while parent:
                level += 1
                parent = parent.parent_id
            record.level = level
    
    @api.depends('parent_id')
    def _compute_is_root(self):
        for record in self:
            record.is_root = not bool(record.parent_id)
    
    @api.depends('parent_id', 'name')
    def _compute_full_path(self):
        for record in self:
            parts = []
            current = record
            while current:
                # Ensure we get the string value of name
                name_value = current.name or ''
                if name_value:
                    parts.insert(0, str(name_value))
                current = current.parent_id
            record.full_path = ' / '.join(parts) if parts else str(record.name or '')
    
    @api.constrains('parent_id')
    def _check_hierarchy_cycle(self):
        if not self._context.get('check_hierarchy_cycle', True):
            return
            
        for record in self:
            if record.parent_id:
                parent = record.parent_id
                while parent:
                    if parent.id == record.id:
                        raise ValidationError(
                            f"Cannot set '{record.name}' as parent of itself "
                            f"or as a descendant. Circular reference detected."
                        )
                    parent = parent.parent_id
    
    @api.constrains('code')
    def _check_unique_code(self):
        for record in self:
            existing = self.search([
                ('code', '=', record.code),
                ('id', '!=', record.id)
            ])
            if existing:
                raise ValidationError(
                    f"Code '{record.code}' already exists! "
                    f"Please use a unique code."
                )
    
    def name_get(self):
        result = []
        for record in self:
            name_parts = []
            current = record
            while current:
                if current.name:
                    name_parts.insert(0, current.name)
                current = current.parent_id
            name = ' / '.join(name_parts) if name_parts else record.name or ''
            result.append((record.id, name))
        return result
    
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            args = ['|', ('name', operator, name), ('code', operator, name)] + args
        return super().name_search(name, args, operator, limit)
    
    @api.model
    def get_root_sources(self):
        return self.search([('parent_id', '=', False)])
    
    def get_ancestors(self):
        ancestors = self.browse()
        parent = self.parent_id
        while parent:
            ancestors |= parent
            parent = parent.parent_id
        return ancestors
    
    def get_descendants(self):
        if not self.parent_path and not self.id:
            return self.browse()
        path = f'{self.parent_path or ""}{self.id}/'
        return self.search([('parent_path', 'like', path)])
    
    def get_siblings(self):
        if not self.parent_id:
            return self.browse()
        return self.search([
            ('parent_id', '=', self.parent_id.id),
            ('id', '!=', self.id)
        ])
    
    def get_full_path(self):
        parts = []
        record = self
        while record:
            if record.name:
                parts.insert(0, record.name)
            record = record.parent_id
        return ' / '.join(parts) if parts else self.name or ''
    
    def action_view_children(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Children of {self.name}',
            'res_model': 'custom.source',
            'view_mode': 'list,form',
            'domain': [('parent_id', '=', self.id)],
            'context': {'default_parent_id': self.id},
            'help': f'List of all sources directly under "{self.name}"'
        }
    
    def action_view_hierarchy(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Hierarchy: {self.name}',
            'res_model': 'custom.source',
            'view_mode': 'list',
            'domain': [('parent_path', 'like', f'{self.parent_path or ""}{self.id}/')],
            'context': {'default_parent_id': self.id},
        }