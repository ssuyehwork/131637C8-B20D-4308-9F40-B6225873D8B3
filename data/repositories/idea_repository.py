# -*- coding: utf-8 -*-
# data/repositories/idea_repository.py
from core.config import COLORS

class IdeaRepository:
    def __init__(self, db_context):
        # 【关键修改】这里必须是 self.db，不能是 self.conn
        self.db = db_context

    def get_count_by_filter(self, search, f_type, f_val, tag_filter=None, criteria=None):
        c = self.db.get_cursor()
        q, p = self._build_query(search, f_type, f_val, tag_filter, criteria, count_only=True)
        c.execute(q, p)
        return c.fetchone()[0]

    def get_list_by_filter(self, search, f_type, f_val, page, page_size, tag_filter=None, criteria=None):
        c = self.db.get_cursor()
        q, p = self._build_query(search, f_type, f_val, tag_filter, criteria, count_only=False)
        
        if f_type == 'trash':
            q += ' ORDER BY i.updated_at DESC'
        else:
            q += ' ORDER BY i.is_pinned DESC, i.updated_at DESC'
            
        if page is not None and page_size is not None:
            limit = page_size
            offset = (page - 1) * page_size
            q += ' LIMIT ? OFFSET ?'
            p.extend([limit, offset])
        
        c.execute(q, p)
        return c.fetchall()

    def _build_query(self, search, f_type, f_val, tag_filter, criteria, count_only=False):
        if count_only:
            q = "SELECT COUNT(DISTINCT i.id) FROM ideas i "
        else:
            q = """
                SELECT DISTINCT 
                    i.id, i.title, i.content, i.color, i.is_pinned, i.is_favorite, 
                    i.created_at, i.updated_at, i.category_id, i.is_deleted, 
                    i.item_type, i.data_blob, i.content_hash, i.is_locked, i.rating
                FROM ideas i 
            """
            
        q += "LEFT JOIN idea_tags it ON i.id=it.idea_id LEFT JOIN tags t ON it.tag_id=t.id WHERE 1=1"
        p = []

        if f_type == 'trash': q += ' AND i.is_deleted=1'
        else: q += ' AND (i.is_deleted=0 OR i.is_deleted IS NULL)'
        
        if f_type == 'category':
            if f_val is None: q += ' AND i.category_id IS NULL'
            else: q += ' AND i.category_id=?'; p.append(f_val)
        elif f_type == 'today': q += " AND date(i.updated_at,'localtime')=date('now','localtime')"
        elif f_type == 'untagged': q += ' AND i.id NOT IN (SELECT idea_id FROM idea_tags)'
        elif f_type == 'bookmark': q += ' AND i.is_favorite=1'
        
        if search:
            q += ' AND (i.title LIKE ? OR i.content LIKE ? OR t.name LIKE ?)'
            p.extend([f'%{search}%']*3)

        if tag_filter:
            q += " AND i.id IN (SELECT idea_id FROM idea_tags WHERE tag_id = (SELECT id FROM tags WHERE name = ?))"
            p.append(tag_filter)
            
        if criteria:
            if 'stars' in criteria:
                stars = criteria['stars']
                placeholders = ','.join('?' * len(stars))
                q += f" AND i.rating IN ({placeholders})"
                p.extend(stars)
            if 'colors' in criteria:
                colors = criteria['colors']
                placeholders = ','.join('?' * len(colors))
                q += f" AND i.color IN ({placeholders})"
                p.extend(colors)
            if 'types' in criteria:
                types = criteria['types']
                placeholders = ','.join('?' * len(types))
                q += f" AND i.item_type IN ({placeholders})"
                p.extend(types)
            if 'tags' in criteria:
                tags = criteria['tags']
                tag_placeholders = ','.join('?' * len(tags))
                q += f" AND i.id IN (SELECT idea_id FROM idea_tags JOIN tags ON idea_tags.tag_id = tags.id WHERE tags.name IN ({tag_placeholders}))"
                p.extend(tags)
            if 'date_create' in criteria:
                date_conditions = []
                for d_opt in criteria['date_create']:
                    if d_opt == 'today': date_conditions.append("date(i.created_at,'localtime')=date('now','localtime')")
                    elif d_opt == 'yesterday': date_conditions.append("date(i.created_at,'localtime')=date('now','-1 day','localtime')")
                    elif d_opt == 'week': date_conditions.append("date(i.created_at,'localtime')>=date('now','-6 days','localtime')")
                    elif d_opt == 'month': date_conditions.append("strftime('%Y-%m',i.created_at,'localtime')=strftime('%Y-%m','now','localtime')")
                if date_conditions:
                    q += " AND (" + " OR ".join(date_conditions) + ")"
        
        return q, p

    def get_by_id(self, iid, include_blob=False):
        c = self.db.get_cursor()
        if include_blob:
            c.execute('SELECT * FROM ideas WHERE id=?', (iid,))
        else:
            c.execute('''
                SELECT id, title, content, color, is_pinned, is_favorite, 
                       created_at, updated_at, category_id, is_deleted, item_type, 
                       NULL as data_blob, NULL as content_hash, is_locked, rating
                FROM ideas WHERE id=?
            ''', (iid,))
        return c.fetchone()

    def add(self, title, content, color, category_id, item_type, data_blob, content_hash=None):
        c = self.db.get_cursor()
        c.execute(
            'INSERT INTO ideas (title, content, color, category_id, item_type, data_blob, content_hash) VALUES (?,?,?,?,?,?,?)',
            (title, content, color, category_id, item_type, data_blob, content_hash)
        )
        self.db.commit()
        return c.lastrowid

    def update(self, iid, title, content, color, category_id, item_type, data_blob):
        c = self.db.get_cursor()
        c.execute(
            'UPDATE ideas SET title=?, content=?, color=?, category_id=?, item_type=?, data_blob=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',
            (title, content, color, category_id, item_type, data_blob, iid)
        )
        self.db.commit()

    def update_field(self, iid, field, value):
        c = self.db.get_cursor()
        c.execute(f'UPDATE ideas SET {field} = ? WHERE id = ?', (value, iid))
        self.db.commit()

    def toggle_field(self, iid, field):
        c = self.db.get_cursor()
        c.execute(f'UPDATE ideas SET {field} = NOT {field} WHERE id=?', (iid,))
        self.db.commit()

    def delete_permanent(self, iid):
        c = self.db.get_cursor()
        c.execute('DELETE FROM ideas WHERE id=?', (iid,))
        c.execute('DELETE FROM idea_tags WHERE idea_id=?', (iid,))
        self.db.commit()

    def get_counts(self):
        c = self.db.get_cursor()
        d = {}
        queries = {
            'all': "is_deleted=0 OR is_deleted IS NULL",
            'today': "(is_deleted=0 OR is_deleted IS NULL) AND date(updated_at,'localtime')=date('now','localtime')",
            'uncategorized': "(is_deleted=0 OR is_deleted IS NULL) AND category_id IS NULL",
            'untagged': "(is_deleted=0 OR is_deleted IS NULL) AND id NOT IN (SELECT idea_id FROM idea_tags)",
            'bookmark': "(is_deleted=0 OR is_deleted IS NULL) AND is_favorite=1",
            'trash': "is_deleted=1"
        }
        for k, v in queries.items():
            c.execute(f"SELECT COUNT(*) FROM ideas WHERE {v}")
            d[k] = c.fetchone()[0]
        
        c.execute("SELECT category_id, COUNT(*) FROM ideas WHERE (is_deleted=0 OR is_deleted IS NULL) GROUP BY category_id")
        d['categories'] = dict(c.fetchall())
        return d
        
    def get_filter_stats(self, search_text, filter_type, filter_value):
        c = self.db.get_cursor()
        stats = {'stars': {}, 'colors': {}, 'types': {}, 'tags': [], 'date_create': {}}
        
        where_clauses = ["1=1"]
        params = []
        
        if filter_type == 'trash': where_clauses.append("i.is_deleted=1")
        else: where_clauses.append("(i.is_deleted=0 OR i.is_deleted IS NULL)")
            
        if filter_type == 'category':
            if filter_value is None: where_clauses.append("i.category_id IS NULL")
            else: where_clauses.append("i.category_id=?"); params.append(filter_value)
        elif filter_type == 'today': where_clauses.append("date(i.updated_at,'localtime')=date('now','localtime')")
        elif filter_type == 'untagged': where_clauses.append("i.id NOT IN (SELECT idea_id FROM idea_tags)")
        elif filter_type == 'bookmark': where_clauses.append("i.is_favorite=1")
        
        if search_text:
            where_clauses.append("(i.title LIKE ? OR i.content LIKE ?)")
            params.extend([f'%{search_text}%', f'%{search_text}%'])
            
        where_str = " AND ".join(where_clauses)
        
        c.execute(f"SELECT i.rating, COUNT(*) FROM ideas i WHERE {where_str} GROUP BY i.rating", params)
        stats['stars'] = dict(c.fetchall())

        c.execute(f"SELECT i.color, COUNT(*) FROM ideas i WHERE {where_str} GROUP BY i.color", params)
        stats['colors'] = dict(c.fetchall())

        c.execute(f"SELECT i.item_type, COUNT(*) FROM ideas i WHERE {where_str} GROUP BY i.item_type", params)
        stats['types'] = dict(c.fetchall())

        tag_sql = f"""
            SELECT t.name, COUNT(it.idea_id) as cnt
            FROM tags t
            JOIN idea_tags it ON t.id = it.tag_id
            JOIN ideas i ON it.idea_id = i.id
            WHERE {where_str}
            GROUP BY t.id
            ORDER BY cnt DESC
        """
        c.execute(tag_sql, params)
        stats['tags'] = c.fetchall()

        base_date_sql = f"SELECT COUNT(*) FROM ideas i WHERE {where_str} AND "
        c.execute(base_date_sql + "date(i.created_at, 'localtime') = date('now', 'localtime')", params)
        stats['date_create']['today'] = c.fetchone()[0]
        c.execute(base_date_sql + "date(i.created_at, 'localtime') = date('now', '-1 day', 'localtime')", params)
        stats['date_create']['yesterday'] = c.fetchone()[0]
        c.execute(base_date_sql + "date(i.created_at, 'localtime') >= date('now', '-6 days', 'localtime')", params)
        stats['date_create']['week'] = c.fetchone()[0]
        c.execute(base_date_sql + "strftime('%Y-%m', i.created_at, 'localtime') = strftime('%Y-%m', 'now', 'localtime')", params)
        stats['date_create']['month'] = c.fetchone()[0]

        return stats
    
    def get_lock_status(self, idea_ids):
        if not idea_ids: return {}
        c = self.db.get_cursor()
        placeholders = ','.join('?' * len(idea_ids))
        c.execute(f'SELECT id, is_locked FROM ideas WHERE id IN ({placeholders})', tuple(idea_ids))
        return dict(c.fetchall())
        
    def set_locked(self, idea_ids, state):
        if not idea_ids: return
        c = self.db.get_cursor()
        val = 1 if state else 0
        placeholders = ','.join('?' * len(idea_ids))
        c.execute(f'UPDATE ideas SET is_locked=? WHERE id IN ({placeholders})', (val, *idea_ids))
        self.db.commit()

    def find_by_hash(self, content_hash):
        c = self.db.get_cursor()
        c.execute("SELECT id FROM ideas WHERE content_hash = ?", (content_hash,))
        return c.fetchone()