# application/services/category_service.py
from typing import List, Optional
from domain.entities import Category
from infrastructure.repositories.category_repository import CategoryRepository
from infrastructure.repositories.idea_repository import IdeaRepository

class CategoryService:
    def __init__(self, category_repository: CategoryRepository, idea_repository: IdeaRepository):
        self._category_repo = category_repository
        self._idea_repo = idea_repository

    def get_all_categories(self) -> List[Category]:
        return self._category_repo.get_all()

    def create_category(self, name: str, parent_id: Optional[int] = None) -> None:
        if not name.strip():
            raise ValueError("Category name cannot be empty.")
        self._category_repo.add(name, parent_id)

    def rename_category(self, category_id: int, new_name: str) -> None:
        if not new_name.strip():
            raise ValueError("Category name cannot be empty.")
        self._category_repo.rename(category_id, new_name)

    def delete_category(self, category_id: int) -> None:
        # Business Logic: before deleting a category, all ideas within it
        # must be moved to 'uncategorized'. The repository handles this now,
        # but this logic should live here.
        # 1. Get all ideas in this category.
        # 2. Move them to category_id = NULL.
        # 3. Delete the category.
        # The current `delete` in repo already does this, which is a temporary design.
        self._category_repo.delete(category_id)

    def set_category_color(self, category_id: int, color: str) -> None:
        # This is a complex operation that involves cascading updates.
        # The repository currently holds this logic. In a pure architecture,
        # the service would fetch all descendant categories and all related ideas,
        # then tell the repositories to update them.
        self._category_repo.set_color(category_id, color)

    def build_category_tree(self) -> List[Category]:
        categories = self._category_repo.get_all()
        category_map = {cat.id: cat for cat in categories}

        tree = []
        for cat in categories:
            if cat.parent_id in category_map:
                parent = category_map[cat.parent_id]
                parent.children.append(cat)
            else:
                tree.append(cat)
        return tree
