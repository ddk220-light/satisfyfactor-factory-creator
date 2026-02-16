from fastapi import APIRouter
from backend.models import AnalyzeRequest, LocationsRequest, AllocateRequest, GenerateRequest
from backend.db import get_db, init_resource_nodes, get_resource_nodes
from backend.engine.recipe_graph import build_recipe_dag, get_raw_demands
from backend.engine.theme_assigner import assign_themes, load_themes
from backend.engine.location_finder import find_locations
from backend.engine.allocator import allocate_production
from backend.engine.plan_generator import generate_factory_plan
from backend.engine.module_builder import compute_modules

router = APIRouter(prefix="/api/plan")


@router.post("/analyze")
def analyze(req: AnalyzeRequest):
    db = get_db()
    init_resource_nodes(db)
    dag = build_recipe_dag(db, req.target_item, req.excluded_recipes)
    themes = load_themes()
    assignments = assign_themes(dag, themes, req.max_factories)
    raw_demands = get_raw_demands(dag, req.target_rate)

    # Serialize DAG for frontend visualization
    dag_nodes = []
    for node in dag.nodes:
        dag_nodes.append({
            "item": node.item,
            "recipe": node.recipe_name,
            "building": node.building,
            "inputs": list(node.inputs.keys()),
            "children": [c.item for c in node.children],
        })

    return {
        "themes": [{"theme": a["theme"], "raw_demands": a["raw_demands"]} for a in assignments],
        "dag": dag_nodes,
        "raw_demands": raw_demands,
    }


@router.post("/locations")
def locations(req: LocationsRequest):
    db = get_db()
    init_resource_nodes(db)
    nodes = get_resource_nodes(db)
    results = {}
    for theme in req.themes:
        results[theme.theme_id] = find_locations(
            nodes, theme.critical_resources,
            req.search_radius_m, req.n_results, req.excluded_quadrants,
        )
    return results


@router.post("/allocate")
def allocate(req: AllocateRequest):
    factories = [f.model_dump() for f in req.factories]
    return allocate_production(factories, req.target_rate, req.train_penalty, req.water_penalty)


@router.post("/generate")
def generate(req: GenerateRequest):
    db = get_db()
    init_resource_nodes(db)
    results = []
    for f in req.factories:
        dag = build_recipe_dag(db, f.target_item, f.excluded_recipes)
        plan = generate_factory_plan(dag, f.allocated_rate, f.local_resources)
        module = compute_modules(dag, plan)
        results.append({
            "theme_id": f.theme_id,
            "plan": plan,
            "module": module,
        })
    return results
