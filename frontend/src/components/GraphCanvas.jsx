/**********************************************************************
 * GraphCanvas.jsx – interactive citation-graph viewer
 * -------------------------------------------------------------------
 *  • streams a prerendered node subset
 *  • tool-tips, ego-highlight, search centering
 *  • NEW ➜ overlay div that shows parent-cluster titles and (when
 *          zoomed in) top sub-cluster labels.
 *********************************************************************/

import React, {
  useLayoutEffect, useEffect, useRef, useState,
} from "react"
import Graph  from "graphology"
import Sigma  from "sigma"

/* ------------------------------------------------------------------ */
/* 1. Constants                                                        */
/* ------------------------------------------------------------------ */
const NODE_SCALE = 50                           // visual node size factor
const API  = import.meta.env.VITE_API_URL        // backend base-url
const NODE_OPACITY  = 0.70;          // one knob for translucency
const GOLDEN_ANGLE  = 137.508;       // irrational ⇒ no repeats
const MIN_PX   = 1;                    // minimum visible size
const MAX_PX   = 8;                 // hero paper
const FNCR_CAP = 1000;              // >1000 rendered as 1000 (for cited_count values)

/* node size ~ log10(score) – tweak multiplier to taste */
function nodeSize(raw) {
  const score = Number(raw) || 0;          // guard NaN / null / undefined
  /* 0 → MIN_PX   …   FNCR_CAP → MAX_PX                     */
  const capped = Math.min(score, FNCR_CAP);
  const t      = Math.log10(capped + 1) / Math.log10(FNCR_CAP + 1); // 0–1
  const size   = MIN_PX + t * (MAX_PX - MIN_PX);

   if (!isFinite(size)) {
     console.warn("[nodeSize] bad score:", raw, "→ size:", size);
     return MIN_PX;
  }
  return size;
}

/* Compute importance score with custom decay factor */
function computeImportanceScore(citations, year, decayFactor = 1.0) {
  const currentYear = new Date().getFullYear();
  const age = Math.max(0, currentYear - (year || 2000));
  const denominator = Math.pow(1 + age, decayFactor);
  return denominator !== 0 ? citations / denominator : 0;
}
// 10 darker pastel anchors: H° values only
const BASE_HUES = [220,30,0,175,140, 50,285,350,25,300];  // last was 0 → 300°

/* helper: HSL (0-360, %, %) → rgba CSS string with shared opacity */
function pastel(h) {
  // 1. h,s,l in [0-1]
  const s = 0.65, l = 0.45;
  const k = n => (n + h / 30) % 12;
  const a = s * Math.min(l, 1 - l);
  const f = n =>
    l - a * Math.max(-1, Math.min(Math.min(k(n) - 3, 9 - k(n)), 1));
  const r = Math.round(f(0)   * 255);
  const g = Math.round(f(8)   * 255);
  const b = Math.round(f(4)   * 255);
  return `rgba(${r},${g},${b},${NODE_OPACITY})`;
}

/* anchors with opacity baked in */
const BASE_COLORS = BASE_HUES.map(pastel);

/* colour for “cluster == -1 / unknown” */
const UNKNOWN_COLOR = `rgba(80,80,80,${NODE_OPACITY})`;

/* total palette function */
function clusterColor(cid) {
  if (cid >= 0 && cid < BASE_COLORS.length) return BASE_COLORS[cid];

  // extra clusters: spin by golden angle from 0°
  const h = (cid * GOLDEN_ANGLE) % 360;
  return pastel(h);
}


/* small helper – millis → "Xm Ys" */
function formatTime(ms){
  if(ms<=0||!isFinite(ms)) return "0s"
  const s=Math.ceil(ms/1000), m=Math.floor(s/60)
  return m ? `${m}m ${s%60}s` : `${s}s`
}

/* ------------------------------------------------------------------ */
/* 2. React component                                                  */
/* ------------------------------------------------------------------ */
export default function GraphCanvas({ onNodeClick, searchResults=[], clusterFilter=[], filters={}, highlightedNode=null, papersOfInterest=new Set(), recommendations=[], hoveredPoiPaper=null }){
  /* 2.1 DOM / lib refs */
  const containerRef    = useRef(null) // sigma container
  const tooltipRef      = useRef(null) // hover tooltip
  const labelsLayerRef  = useRef(null) // parent div for overlay labels
  const labelSpansRef   = useRef({})   // cid → span element

  const graphRef        = useRef(null)
  const sigmaRef        = useRef(null)
  // remembers only the nodes we recoloured during the last highlight
  const changedNodeColors = useRef(new Map())   // nodeId → previousColour
  const egoEdgesSet       = useRef(new Set())   // temp edges we add
  /* live filter set — the nodeReducer reads from this */
  const filterRef = useRef(new Set(clusterFilter));
  
  // Refs for nodeReducer to access latest POI/rec/hover values
  const hoveredPoiPaperRef = useRef(hoveredPoiPaper);
  const papersOfInterestRef = useRef(papersOfInterest);
  const recommendationsRef = useRef(recommendations);
  
  // Keep refs in sync
  useEffect(() => {
    hoveredPoiPaperRef.current = hoveredPoiPaper;
    papersOfInterestRef.current = papersOfInterest;
    recommendationsRef.current = recommendations;
  }, [hoveredPoiPaper, papersOfInterest, recommendations]);
  useEffect(() => {
    // Store both cluster filter and other filters
    const newFilter = new Set(clusterFilter);
    newFilter.yearMin = filters?.yearMin;
    newFilter.yearMax = filters?.yearMax;
    newFilter.minCitations = filters?.minCitations;
    filterRef.current = newFilter;
    
    // Force complete re-render to update all nodes immediately
    if (sigmaRef.current) {
      sigmaRef.current.refresh();
      // Trigger additional refresh to ensure all nodes update
      requestAnimationFrame(() => {
        sigmaRef.current?.refresh();
      });
    }
  }, [clusterFilter, filters]);

  /* 2.2 UI state (loading bar) */
  const [nodesTotal,setNodesTotal]             = useState(0)
  const [loadedNodes,setLoadedNodes]           = useState(0)
  const [loadingStart,setLoadingStart]         = useState(null)
  const [finishedLoading,setFinishedLoading]   = useState(false)

  /* 2.3 parent / sub-cluster meta fetched once */
  const [clustersMeta,setClustersMeta] = useState([])
  
  /* 2.4 Highlight node from external hover (e.g., search sidebar) with delay */
  useEffect(() => {
    const graph = graphRef.current;
    const renderer = sigmaRef.current;
    if (!graph || !renderer) return;
    
    // No highlight if no node specified
    if (!highlightedNode) return;
    
    // 1 second delay before highlighting
    const timeoutId = setTimeout(() => {
      // Check if node exists in graph
      if (!graph.hasNode(highlightedNode)) return;
      
      // Store original size
      const originalSize = graph.getNodeAttribute(highlightedNode, 'size');
      const enlargedSize = originalSize * 2.5;
      
      // Gray out all other nodes and enlarge the highlighted one
      graph.forEachNode((nodeId) => {
        if (nodeId === highlightedNode) {
          // Enlarge and make red
          graph.setNodeAttribute(nodeId, 'color', '#FF6B6B');
          graph.setNodeAttribute(nodeId, 'size', enlargedSize);
        } else {
          // Gray out others
          graph.setNodeAttribute(nodeId, 'color', '#CCCCCC');
        }
      });
      
      renderer.refresh();
    }, 1000); // 1 second delay
    
    // Cleanup: restore all nodes immediately when hover ends
    return () => {
      clearTimeout(timeoutId);
      
      if (graph && renderer) {
        graph.forEachNode((nodeId) => {
          const origColor = graph.getNodeAttribute(nodeId, 'origColor');
          if (origColor) {
            graph.setNodeAttribute(nodeId, 'color', origColor);
          }
          
          // Restore size for highlighted node
          if (nodeId === highlightedNode) {
            const citations = graph.getNodeAttribute(nodeId, 'cited_count') || 0;
            const year = graph.getNodeAttribute(nodeId, 'year');
            const decayFactor = filters?.decayFactor || 1.0;
            const score = computeImportanceScore(citations, year, decayFactor);
            const normalSize = nodeSize(score);
            graph.setNodeAttribute(nodeId, 'size', normalSize);
          }
        });
        renderer.refresh();
      }
    };
  }, [highlightedNode, filters?.decayFactor]);

  /* 2.5 Recompute node sizes when decay factor changes */
  useEffect(() => {
    const graph = graphRef.current;
    const renderer = sigmaRef.current;
    if (!graph || !renderer) return;

    const decayFactor = filters?.decayFactor || 1.0;
    
    // Recompute size for all nodes based on new decay factor
    graph.forEachNode((nodeId) => {
      const citations = graph.getNodeAttribute(nodeId, 'cited_count') || 0;
      const year = graph.getNodeAttribute(nodeId, 'year');
      
      const newScore = computeImportanceScore(citations, year, decayFactor);
      const newSize = nodeSize(newScore);
      
      graph.setNodeAttribute(nodeId, 'size', newSize);
    });
    
    renderer.refresh();
  }, [filters?.decayFactor]);

  /* 2.6 Auto-load Papers of Interest nodes into graph */
  useEffect(() => {
    if (!papersOfInterest || papersOfInterest.size === 0) return;
    
    // Load each POI paper if not already in graph
    papersOfInterest.forEach(async (doi) => {
      await loadMissingNode(doi);
    });
  }, [papersOfInterest]);
  
  /* 2.7 Auto-load recommendation nodes into graph */
  useEffect(() => {
    if (!recommendations || recommendations.length === 0) return;
    
    // Load each recommended paper if not already in graph
    recommendations.forEach(async (rec) => {
      await loadMissingNode(rec.doi);
    });
  }, [recommendations]);

  /* 2.8 Force refresh when POI/recommendations/hover changes        */
  useEffect(() => {
    const renderer = sigmaRef.current;
    if (renderer) {
      console.log('Refreshing graph - hover:', hoveredPoiPaper, 'POI count:', papersOfInterest.size, 'Recs:', recommendations.length);
      renderer.refresh();
    }
  }, [papersOfInterest, recommendations, hoveredPoiPaper]);

  /* --------------------------------------------------------------- */
  /* 3. Derived helpers                                              */
  /* --------------------------------------------------------------- */
  const isStillLoading = !finishedLoading
  const timeLeftMs = loadingStart && loadedNodes
    ? (Date.now()-loadingStart) * (nodesTotal/loadedNodes - 1)
    : 0

  /* --------------------------------------------------------------- */
  /* 4. Tooltip helpers (unchanged)                                  */
  /* --------------------------------------------------------------- */
  async function showTip(node){
    const graph=graphRef.current, renderer=sigmaRef.current
    if(!graph||!renderer) return

    const attrs=graph.getNodeAttributes(node)
    /* lazy-load metadata if missing authors or title */
    if(!attrs.authors || !attrs.title){
      try{
        // Cache-bust paper details fetch to avoid stale caching across graph switches
        const r=await fetch(`${API}/paper/${encodeURIComponent(node)}?v=${Date.now()}`)
        if(r.ok){
          const md=await r.json()
          graph.setNodeAttribute(node,"title",md.title)
          graph.setNodeAttribute(node,"authors",md.authors)
          graph.setNodeAttribute(node,"year",md.year)
          graph.setNodeAttribute(node,"cited_count",md.cited_count)
          graph.setNodeAttribute(node, 'fncr',  md.fncr_count ?? md.fncr)
        }
      }catch(e){ console.warn("meta fetch failed",e) }
    }
    /* build tooltip html */
    const u=graph.getNodeAttributes(node)
    const decayFactor = filters?.decayFactor || 1.0;
    const importanceScore = computeImportanceScore(u.cited_count || 0, u.year, decayFactor);
    tooltipRef.current.innerHTML=`<strong>${u.title||"No title"}</strong><br/>
      <em>Authors:</em> ${(u.authors||[]).join(", ") || "Unknown"}<br/>
      <em>Year:</em> ${u.year??"N/A"} • <em>Cited:</em> ${u.cited_count??0} • <em>Score:</em> ${importanceScore.toFixed(2)}`;

    const d=renderer.getNodeDisplayData(node)
    tooltipRef.current.style.left  =`${d.x+8}px`
    tooltipRef.current.style.top   =`${d.y+8}px`
    tooltipRef.current.style.display="block"
  }

/* --------------------------------------------------------------- */
/* 4.7 Helper: Load missing nodes into graph                       */
/* --------------------------------------------------------------- */
async function loadMissingNode(doi) {
  const graph = graphRef.current;
  const renderer = sigmaRef.current;
  if (!graph || !renderer) return false;
  
  if (graph.hasNode(doi)) return true; // Already loaded
  
  try {
    const res = await fetch(`${API}/paper/${encodeURIComponent(doi)}`);
    if (!res.ok) return false;
    
    const paper = await res.json();
    if (paper.x == null || paper.y == null) return false; // No position
    
    const cid = Number.isFinite(paper.cluster) ? paper.cluster : parseInt(paper.cluster, 10);
    const color = cid >= 0 ? clusterColor(cid) : UNKNOWN_COLOR;
    
    graph.addNode(doi, {
      x: paper.x,
      y: paper.y,
      size: 3, // Slightly larger for manually loaded nodes
      color: color,
      origColor: color,
      cluster: paper.cluster,
      year: paper.year,
      cited_count: paper.cited_count,
      title: paper.title,
      manualLoad: true, // Mark as manually loaded
    });
    
    renderer.refresh();
    return true;
  } catch (e) {
    console.warn(`Failed to load node ${doi}:`, e);
    return false;
  }
}

/* --------------------------------------------------------------- */
/* 5. Ego highlight (efficient, no graph.batch needed)             */
/* --------------------------------------------------------------- */

/** Undo any previous highlight. */
function clearHighlight() {
  const graph    = graphRef.current;
  const renderer = sigmaRef.current;
  if (!graph) return;

  /* 1 ─ drop the temporary ego edges */
  egoEdgesSet.current.forEach(key => {
    if (graph.hasEdge(key)) graph.dropEdge(key);
  });
  egoEdgesSet.current.clear();

  /* 2 ─ restore the colours we changed last time */
  changedNodeColors.current.forEach((prev, id) => {
    if (graph.hasNode(id)) graph.setNodeAttribute(id, "color", prev);
  });
  changedNodeColors.current.clear();

  /* 3 ─ redraw once */
  renderer?.refresh();
}

/** Highlight the chosen paper and its direct neighbours. */
async function highlightNode(doi) {
  const graph    = graphRef.current;
  const renderer = sigmaRef.current;
  if (!graph) return;

  /* 1 ─ clear any previous highlight */
  clearHighlight();

  try {
    /* 2 ─ fetch the ego-net (depth 1 gives centre + neighbours) */
    const r = await fetch(`${API}/ego?doi=${encodeURIComponent(doi)}&depth=1`);
    if (!r.ok) throw new Error("ego fetch failed");
    const { nodes: egoNodes = [], edges: egoEdges = [] } = await r.json();

    /* --------------------------------------------------------- */
    /* 3 ─ build *one* patch object with only the *new* items    */
    /* --------------------------------------------------------- */
    const patch = { nodes: [], edges: [] };

    /* 3-a ─ nodes                                                 */
    egoNodes.forEach(n => {
      if (graph.hasNode(n.id)) return;          // already in graph
      const size  = nodeSize(n.fncr ?? 0);
      /* eslint-disable-next-line no-console */
      console.debug("ego node", n.id, "fncr=", n.fncr, "→ size", size);
      const cid   = n.cluster ?? -1;
      const color = cid >= 0 ? clusterColor(cid) : UNKNOWN_COLOR;
      patch.nodes.push({
        key: n.id,
        attributes: { x: n.x, y: n.y, size, color,
                      origColor: color, cluster: cid }
      });
    });

    /* 3-b ─ edges (only those that touch the centre node)         */
    egoEdges.forEach(e => {
      if (e.source !== doi && e.target !== doi) return;          // skip neighbour↔neighbour
      if (!graph.hasNode(e.source) || !graph.hasNode(e.target)) return;
      const key = `${e.source}|${e.target}`;
      if (graph.hasEdge(key)) return;

      const col = e.source === doi ? "#00FF00" : "#FF0000";
      patch.edges.push({
        key,
        source: e.source,
        target: e.target,
        attributes: { size: 0.001, color: col, origColor: col }
      });
      egoEdgesSet.current.add(key);           // remember for cleanup
    });

    /* 3-c ─ one *silent* bulk insert                             */
    if (patch.nodes.length || patch.edges.length) graph.import(patch);

    /* --------------------------------------------------------- */
    /* 4 ─ recolour the centre + its direct neighbours           */
    /* --------------------------------------------------------- */
    function recolor(id, newCol) {
      if (!graph.hasNode(id)) return;
      if (!changedNodeColors.current.has(id)) {
        changedNodeColors.current.set(id, graph.getNodeAttribute(id, "color"));
      }
      graph.setNodeAttribute(id, "color", newCol);
    }

    recolor(doi,  "#0033ff");      // blue focus
    graph.forEachOutboundNeighbor(doi, n => recolor(n, "#00c853")); // cites
    graph.forEachInboundNeighbor (doi, n => recolor(n, "#d50000")); // cited by

    /* --------------------------------------------------------- */
    /* 5 ─ single refresh                                        */
    /* --------------------------------------------------------- */
    renderer.refresh();
    onNodeClick?.(doi);

  } catch (err) {
    console.warn(err);
  }
}

  /* ------------------------------------------------------------------ */
/* 6. Overlay labels (parent + sub-clusters)                          */
/* ------------------------------------------------------------------ */
useEffect(() => {
  const renderer  = sigmaRef.current;
  const container = containerRef.current;
  if (!renderer || !container || !clustersMeta.length) return;

  /* ---------- 6.1 overlay root (one per mount) ------------------ */
  let layer = labelsLayerRef.current;
  if (!layer) {
    layer = document.createElement("div");
    layer.style.cssText = `
      position:absolute; inset:0;
      overflow:hidden;                    /* confine to graph pane   */
      pointer-events:none; z-index:20;    /* below sidebar           */
      font-family:inherit; user-select:none;`;
    container.parentElement.appendChild(layer);
    labelsLayerRef.current = layer;
  }

  /* ---------- 6.2 ensure one <span> per cluster ----------------- */
  clustersMeta.forEach(c => {
    if (labelSpansRef.current[c.id]) return;
    const span = document.createElement("span");
    span.textContent = c.label ?? c.title ?? c.name ?? `Cluster ${c.id}`;
    span.className   = (c.level ?? "parent") + "-label";
    span.style.cssText = `
      position:absolute; transform:translate(-50%,-50%);
      white-space:nowrap; font-weight:600; color:#333;
      opacity:0; transition:opacity .25s;`;
    layer.appendChild(span);
    labelSpansRef.current[c.id] = span;
  });

  const cam = renderer.getCamera();

  /* ---------- 6.3 helpers --------------------------------------- */
  function placeLabels() {
    clustersMeta.forEach(c => {
      /* ───── filter by current sidebar selection ───── */
      const idNum = Number.isFinite(c.id) ? c.id : parseInt(c.id.split(":").pop(),10);
      const parentNum = c.parent_id !== undefined
        ? +c.parent_id
        : (c.id.includes?.(":") ? +c.id.split(":")[0] : undefined);

      const keep =
        !filterRef.current.size ||          // nothing filtered yet
        filterRef.current.has(idNum) ||
        (parentNum !== undefined && filterRef.current.has(parentNum));

      if (!keep) return;                    // hide & skip positioning

      const span = labelSpansRef.current[c.id];
      if (!span) return;
      const { x, y } = renderer.graphToViewport({ x: c.x, y: c.y });
      span.style.left = `${x}px`;
      span.style.top  = `${y}px`;
    });
  }

  function updateVisibilityAndCull() {
    const z = cam.getState().ratio;           // 1 = zoomed-out

    /* 1 ─ raw visibility */
    clustersMeta.forEach((c, idx) => {
      const span = labelSpansRef.current[c.id];
      if (!span) return;

      /* filter check (same logic as above) */
      const idNum     = Number.isFinite(c.id) ? c.id : parseInt(c.id.split(":").pop(),10);
      const parentNum = c.parent_id !== undefined
        ? +c.parent_id
        : (c.id.includes?.(":") ? +c.id.split(":")[0] : undefined);
      const keep =
        !filterRef.current.size ||
        filterRef.current.has(idNum) ||
        (parentNum !== undefined && filterRef.current.has(parentNum));
      if (!keep) { span.style.opacity = 0; return; }

      const isParent = c.level === "parent" || c.level === undefined;
      const visible  = isParent
        ? (z > 0.6 ? idx < 30 : z > 0.3 ? true : c.rand < 0.35)
        : z <= 0.3;
      span.style.opacity = visible ? 1 : 0;
    });

    /* 2 ─ collision culling (largest clusters win) */
    const visibleSpans = clustersMeta
      .filter(c => labelSpansRef.current[c.id].style.opacity > 0)
      .sort((a, b) => (b.size ?? 0) - (a.size ?? 0));

    const taken = [];
    visibleSpans.forEach(c => {
      const span = labelSpansRef.current[c.id];
      const { offsetWidth:w, offsetHeight:h } = span;
      const x = parseFloat(span.style.left);
      const y = parseFloat(span.style.top);
      const box = { x1:x-w/2, y1:y-h/2, x2:x+w/2, y2:y+h/2 };
      const overlaps = taken.some(t =>
        !(t.x2 < box.x1 || t.x1 > box.x2 || t.y2 < box.y1 || t.y1 > box.y2));
      if (overlaps) span.style.opacity = 0;
      else          taken.push(box);
    });
  }

  /* ---------- 6.4 throttle expensive part ----------------------- */
  let idleTimer = null;                 // fires after camera stops
  function handleCamUpdate() {
    placeLabels();                      // cheap → every tick
    clearTimeout(idleTimer);
    idleTimer = setTimeout(updateVisibilityAndCull, 120);
  }

  cam.on("updated", handleCamUpdate);
  handleCamUpdate();                    // run once now

  /* ---------- 6.5 cleanup --------------------------------------- */
  return () => {
    cam.off?.("updated", handleCamUpdate);
    cam.removeListener?.("updated", handleCamUpdate);
    Object.values(labelSpansRef.current).forEach(el => el.remove());
    labelSpansRef.current = {};
    if (labelsLayerRef.current) {
      labelsLayerRef.current.remove();
      labelsLayerRef.current = null;
    }
    clearTimeout(idleTimer);
  };
}, [clustersMeta, clusterFilter]);


  /* --------------------------------------------------------------- */
  /* 7. Initial node subset streaming                                */
  /* --------------------------------------------------------------- */
  async function loadInitialNodes(){
    // Get node limit from localStorage if set
    const nodeLimit = localStorage.getItem('graphNodeLimit');
    
    // Build URL with optional top_n parameter
    const cacheBuster = Date.now();
    let url = `${API}/export/initial.ndjson?v=${cacheBuster}`;
    if (nodeLimit) {
      url = `${API}/export/initial.ndjson?top_n=${encodeURIComponent(nodeLimit)}&v=${cacheBuster}`;
    }
    
    const r=await fetch(url)
    if(!r.ok) { console.error("initial.ndjson failed"); return }
    const txt=await r.text()
    const lines=txt.split("\n")
    const graph=graphRef.current
    const total = lines.reduce((c,l)=>{
      if(!l.trim()) return c
      try{return JSON.parse(l).type==="node"?c+1:c}catch{return c}
    },0)
    setNodesTotal(total); setLoadingStart(Date.now())
    let batch=0
    for(const line of lines){
      if(!line.trim()) continue
      let obj; try{obj=JSON.parse(line)}catch{continue}
      if(obj.type!=="node") continue
      if(graph.hasNode(obj.id)) continue
      
      // Compute score with custom decay factor if available
      const decayFactor = filters?.decayFactor || 1.0;
      const score = computeImportanceScore(
        obj.cited_count || 0,
        obj.year,
        decayFactor
      );
      
      if (loadedNodes === 0 && batch < 5) {
        /* eslint-disable-next-line no-console */
        console.debug("stream node", obj.id, "score=", score.toFixed(2), "year=", obj.year, "decay=", decayFactor);
      }
      const size = nodeSize(score);
      const cid=obj.cluster??-1
      const color = cid >= 0 ? clusterColor(cid) : UNKNOWN_COLOR;
      graph.addNode(obj.id,{
        x:obj.x,
        y:obj.y,
        size,
        color,
        origColor:color,
        cluster:cid,
        year: obj.year,
        cited_count: obj.cited_count,
        title: obj.title
      })
      if(++batch>=200){
        setLoadedNodes(n=>n+batch); batch=0; sigmaRef.current.refresh()
        await new Promise(r=>setTimeout(r,0))
      }
    }
    if(batch){ setLoadedNodes(n=>n+batch); sigmaRef.current.refresh() }
    setFinishedLoading(true)
    
    // Fit camera to show all nodes
    if(sigmaRef.current && graph.size > 0) {
      sigmaRef.current.getCamera().animate(sigmaRef.current.getBbox(), {duration: 1000})
    }
  }

  /* --------------------------------------------------------------- */
  /* 8. Mount – initialise Sigma + overlay                           */
  /* --------------------------------------------------------------- */
  useLayoutEffect(()=>{
    let renderer;              // keep local for cleanup

    (async()=>{
      /* 8.1 Sigma container */
      const container=containerRef.current
      if(!container) return
      console.info("[GraphCanvas] Sigma renderer created, NODE_SCALE=", NODE_SCALE);
      const graph=new Graph()
      graphRef.current=graph
      renderer=new Sigma(graph,container,{
        renderLabels:false,defaultNodeType:"circle",defaultEdgeType:"line",
        enableNodeHoverEvents:false,enableEdgeHoverEvents:false,
        allowInvalidContainer:true,

        /* thin outline on every node */
         nodeReducer: (id, data) => {
          /* base styling (same as before) */
          const base = {
            ...data,
            borderColor : "rgba(0,0,0,0.35)",
            borderWidth : data.size < 3 ? 0.8 : 1,
          };

          /* hide if the node's parent cluster isn't in the filter */
          if (filterRef.current.size &&
              !filterRef.current.has(data.cluster)) {
            return { ...base, hidden: true };
          }
          
          /* hide nodes outside date range filter */
          const yearMin = filterRef.current.yearMin;
          const yearMax = filterRef.current.yearMax;
          if (yearMin && data.year && data.year < yearMin) {
            return { ...base, hidden: true };
          }
          if (yearMax && data.year && data.year > yearMax) {
            return { ...base, hidden: true };
          }
          
          /* hide nodes below citation threshold */
          const minCitations = filterRef.current.minCitations;
          if (minCitations && data.cited_count != null && data.cited_count < minCitations) {
            return { ...base, hidden: true };
          }
          
          /* Grey out everything except POI/recs when hovering in My Papers tab */
          if (hoveredPoiPaperRef.current !== null) {
            const isPoi = papersOfInterestRef.current.has(id);
            const isRec = recommendationsRef.current.some(rec => rec.doi === id);
            const isHovered = id === hoveredPoiPaperRef.current;
            
            if (!isPoi && !isRec) {
              // Grey out non-POI/rec papers
              return {
                ...base,
                color: "#ddd",
                hidden: false,
                zIndex: 1,
              };
            } else if (isHovered) {
              // Highlight the hovered paper with STRONG gold
              return {
                ...base,
                size: base.size * 2.0,
                color: "#FFD700", // Fill with gold
                borderColor: "#FF8C00", // Dark orange border
                borderWidth: 5,
                zIndex: 15,
              };
            } else if (isPoi) {
              // Keep other POI papers highlighted with gold theme
              return {
                ...base,
                size: base.size * 1.5,
                color: data.origColor, // Keep cluster color
                borderColor: "#FFD700", // Gold border
                borderWidth: 3,
                zIndex: 10,
              };
            } else if (isRec) {
              // Keep recommendations highlighted with CYAN theme (distinct from gold)
              return {
                ...base,
                size: base.size * 1.3,
                color: "#87CEEB", // Sky blue fill
                borderColor: "#17a2b8", // Cyan border
                borderWidth: 2.5,
                zIndex: 9,
              };
            }
          }
          
          /* Normal highlighting (no hover) */
          /* highlight papers in "My Papers" collection */
          if (papersOfInterestRef.current.has(id)) {
            return {
              ...base,
              size: base.size * 1.5,
              borderColor: "#FFD700", // gold
              borderWidth: 3,
              zIndex: 10, // render on top
            };
          }
          
          /* highlight recommended papers */
          const isRecommended = recommendationsRef.current.some(rec => rec.doi === id);
          if (isRecommended) {
            return {
              ...base,
              size: base.size * 1.3,
              borderColor: "#17a2b8", // cyan
              borderWidth: 2.5,
              zIndex: 9, // render on top but below Papers of Interest
            };
          }
          
          return base;
        },
      })
      sigmaRef.current=renderer

      /* 8.2 tooltip div */
      const tip=document.createElement("div")
      tip.style.cssText=`
        position:absolute;pointer-events:none;z-index:100;
        background:rgba(0,0,0,.75);color:#fff;font-size:.8rem;
        padding:6px 10px;border-radius:4px;display:none;max-width:280px;`
      container.parentElement.appendChild(tip)
      tooltipRef.current=tip


      /* 8.4 node events */
      renderer.on("enterNode",({node})=>showTip(node))
      renderer.on("leaveNode",()=>{tooltipRef.current.style.display="none"})
      let lastClick = 0;
renderer.on("clickNode", async ({node}) => {
  const now = Date.now();
  if (now - lastClick < 250) return;   // ¼-second guard
  lastClick = now;
  tooltipRef.current.style.display = "none";
  await highlightNode(node);
  // Update selected DOI in parent component
  onNodeClick(node);
});
      renderer.on("clickStage",()=>{clearHighlight()})

      /* 8.5 fetch clusters meta & build overlay */
      try{
        const r=await fetch(`${API}/clusters?v=${Date.now()}`)
        console.log(r)
        if(r.ok){
          const meta=await r.json()
          /* keep biggest first */
          meta.sort((a,b)=>b.size-a.size)
          /* store one stable random for each cluster (avoids flicker) */
          meta.forEach(c => { c.rand = Math.random(); });
          setClustersMeta(meta)
        }
      }catch(e){ console.warn("cluster meta fetch failed",e) }

      /* 8.6 load initial nodes (async) */
      await loadInitialNodes()
    })()

    /* cleanup */
    return ()=>{
      renderer?.kill()
      tooltipRef.current?.remove()
      labelsLayerRef.current?.remove()
    }
  },[])

  /* 8.7 once clustersMeta is ready – build overlay div */

  /* --------------------------------------------------------------- */
  /* 9. Center camera on search result                               */
  /* --------------------------------------------------------------- */
  useEffect(()=>{
    if(!searchResults.length) return
    const doi=searchResults[0], renderer=sigmaRef.current, graph=graphRef.current
    if(!renderer||!graph) return
    if(graph.hasNode(doi)){
      const d=renderer.getNodeDisplayData(doi)
      renderer.getCamera().animate({x:d.x,y:d.y,ratio:0.95},{duration:800})
      highlightNode(doi)
    }else highlightNode(doi)
  },[searchResults])

  /* --------------------------------------------------------------- */
  /* 9.5 LOD: Load additional nodes when zoomed in                   */
  /* --------------------------------------------------------------- */
  useEffect(() => {
    const renderer = sigmaRef.current;
    const graph = graphRef.current;
    if (!renderer || !graph || !clustersMeta.length) return;

    let lodTimer = null;
    let lastZoom = renderer.getCamera().ratio;
    const lodNodes = new Set(); // Track nodes added via LOD
    const lodEdges = new Set(); // Track edges added via LOD

    const handleCameraUpdate = () => {
      clearTimeout(lodTimer);
      lodTimer = setTimeout(async () => {
        const camera = renderer.getCamera();
        const zoom = camera.ratio;
        
        // Remove LOD nodes when zoomed out (ratio >= 0.5)
        if (zoom >= 0.5) {
          if (lodNodes.size > 0) {
            console.log(`LOD: Removing ${lodNodes.size} nodes (zoomed out to ${zoom.toFixed(2)})`);
            
            // Batch drop nodes to avoid stuttering
            graph.updateGraph(() => {
              lodNodes.forEach(doi => {
                if (graph.hasNode(doi)) graph.dropNode(doi);
              });
            });
            
            lodNodes.clear();
            lodEdges.clear();
            // No need for manual refresh - updateGraph handles it
          }
          lastZoom = zoom;
          return;
        }
        
        // Avoid redundant fetches if zoom hasn't changed much
        if (Math.abs(zoom - lastZoom) < 0.1) return;
        lastZoom = zoom;

        // Calculate viewport bounds
        const { width, height } = renderer.getDimensions();
        const viewportCorner1 = renderer.viewportToGraph({ x: 0, y: 0 });
        const viewportCorner2 = renderer.viewportToGraph({ x: width, y: height });
        
        const x_min = Math.min(viewportCorner1.x, viewportCorner2.x);
        const x_max = Math.max(viewportCorner1.x, viewportCorner2.x);
        const y_min = Math.min(viewportCorner1.y, viewportCorner2.y);
        const y_max = Math.max(viewportCorner1.y, viewportCorner2.y);

        // Dynamic citation threshold: lower threshold when more zoomed in
        const minCitations = Math.max(0, Math.floor(25 * zoom));

        try {
          const response = await fetch(
            `${API}/lod/nodes?x_min=${x_min}&x_max=${x_max}&y_min=${y_min}&y_max=${y_max}&min_citations=${minCitations}&limit=500`
          );
          
          if (!response.ok) return;
          
          const data = await response.json();
          let addedCount = 0;
          
          // Add new nodes to graph with cluster colors
          data.nodes.forEach(node => {
            if (!graph.hasNode(node.doi)) {
              // Use the same color function as initial nodes
              const cid = Number.isFinite(node.cluster) ? node.cluster : parseInt(node.cluster, 10);
              const color = cid >= 0 ? clusterColor(cid) : UNKNOWN_COLOR;
              
              graph.addNode(node.doi, {
                x: node.x,
                y: node.y,
                size: 2,
                color: color,
                origColor: color,
                cluster: node.cluster,
                year: node.year,
                cited_count: node.cited_count,
                title: node.title,
                lodNode: true, // Mark as LOD-loaded
              });
              lodNodes.add(node.doi);
              addedCount++;
            }
          });
          
          // Add edges but mark them as hidden (only show when node is selected)
          data.edges.forEach(edge => {
            const edgeId = `${edge.source}-${edge.target}`;
            if (!graph.hasEdge(edgeId) && graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
              graph.addEdge(edge.source, edge.target, { 
                size: 0.5,
                hidden: true, // Hide by default
                lodEdge: true,
              });
              lodEdges.add(edgeId);
            }
          });
          
          if (addedCount > 0) {
            console.log(`LOD: Added ${addedCount} nodes at zoom=${zoom.toFixed(2)}`);
            renderer.refresh();
          }
        } catch (e) {
          console.warn("LOD fetch failed", e);
        }
      }, 300); // Debounce 300ms
    };

    const camera = renderer.getCamera();
    camera.on("updated", handleCameraUpdate);

    return () => {
      camera.off("updated", handleCameraUpdate);
      clearTimeout(lodTimer);
      // Clean up LOD nodes on unmount
      lodNodes.forEach(doi => {
        if (graph.hasNode(doi)) graph.dropNode(doi);
      });
    };
  }, [clustersMeta])

  /* --------------------------------------------------------------- */
  /* 10. Render                                                      */
  /* --------------------------------------------------------------- */
  return(
    <div style={{position:"relative",width:"100%",height:"100%"}}>
      {/* loading overlay */}
      {isStillLoading&&(
        <div style={{
          position:"absolute",top:"50%",left:"50%",
          transform:"translate(-50%,-50%)",
          background:"rgba(255,255,255,.92)",padding:"12px 16px",
          borderRadius:"6px",textAlign:"center",zIndex:10,minWidth:"240px",
          boxShadow:"0 2px 8px rgba(0,0,0,.25)"
        }}>
          <div style={{marginBottom:"8px",fontSize:".9rem",color:"#333"}}>
            Nodes: {loadedNodes.toLocaleString()} / {nodesTotal.toLocaleString()}<br/>
            ETA: {formatTime(timeLeftMs)}
          </div>
          <div style={{
            width:"200px",height:"8px",background:"#eee",
            borderRadius:"4px",overflow:"hidden",margin:"0 auto"
          }}>
            <div style={{
              width:`${Math.round(loadedNodes/nodesTotal*100)}%`,
              height:"100%",background:"#007bff",transition:"width .2s"
            }}/>
          </div>
        </div>
      )}
      {/* sigma container */}
      <div ref={containerRef} className="graph-container"
           style={{width:"100%",height:"100%"}} />
    </div>
  )
}
