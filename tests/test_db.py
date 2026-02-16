# tests/test_db.py
import pytest
from backend.db import get_db, init_resource_nodes, get_resource_nodes


def test_resource_nodes_loaded():
    db = get_db()
    init_resource_nodes(db)
    nodes = get_resource_nodes(db)
    assert len(nodes) > 400  # game has 459 resource nodes
    node = nodes[0]
    assert "type" in node
    assert "purity" in node
    assert "x" in node and "y" in node


def test_items_table_exists():
    db = get_db()
    cursor = db.execute("SELECT COUNT(*) FROM items")
    count = cursor.fetchone()[0]
    assert count > 100  # game has hundreds of items
