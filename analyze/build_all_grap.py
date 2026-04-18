import json
import glob
import os
from datetime import datetime
import networkx as nx
from pyvis.network import Network

# ====================== ФУНКЦИЯ ПОСТРОЕНИЯ ГРАФА ИЗ ОДНОГО СРЕЗА ======================
def build_graph_from_slice(analysis, slice_id):
    G = nx.DiGraph()
    
    # 1. Мета-узел Source
    G.add_node(slice_id, 
               type="Source",
               label=f"Step {slice_id.split('_')[-1]}",
               mood=analysis.get('mood', 'neutral'),
               self_score=round(analysis.get('self_referential_score', 0.0), 2),
               title=f"Mood: {analysis.get('mood')}\nScore: {analysis.get('self_referential_score'):.2f}")
    
    # 2. Обработка SVO из всех предложений
    for sent in analysis.get('sentences', []):
        sent_id = sent.get('sentence_id', 0)
        for svo in sent.get('svo_triples', []):
            subj = str(svo.get('subject', '')).strip()
            verb = str(svo.get('verb', '')).strip().lower()
            obj = str(svo.get('object', '')).strip() if svo.get('object') is not None else None
            
            if not subj:
                continue
                
            # Нормализация центрального персонажа
            if subj.lower() in ['jammingbot', 'bot', 'this', 'that', 'он', 'он']:
                subj_node = "Bot"
            else:
                subj_node = subj[:70]
            
            G.add_node(subj_node, type="Entity")
            G.add_edge(slice_id, subj_node, relation="CONTAINS")
            
            if obj:
                if obj.lower() in ['bot', 'this', 'that', 'он']:
                    obj_node = "Bot"
                else:
                    obj_node = obj[:70]
                
                G.add_node(obj_node, type="Entity")
                G.add_edge(subj_node, obj_node,
                          label=verb,
                          verb=verb,
                          from_slice=slice_id,
                          from_sentence=sent_id)
            else:
                action_node = f"{subj_node}_{verb}"
                G.add_node(action_node, type="Action", label=verb.upper())
                G.add_edge(subj_node, action_node,
                          label=verb,
                          verb=verb,
                          from_slice=slice_id)
    
    # 3. Ключевые фразы
    for phrase in analysis.get('global', {}).get('key_phrases', [])[:12]:
        if len(phrase.strip()) > 3:
            clean = phrase.strip()[:80]
            G.add_node(clean, type="KeyPhrase")
            G.add_edge(slice_id, clean, relation="HAS_KEYPHRASE")
    
    return G

# ====================== ОСНОВНОЙ СКРИПТ ======================
def main():
    # Находим все step_*.json
    files = sorted(glob.glob("steps/step_*.json"))
    print(f"Найдено {len(files)} файлов шагов.")
    
    if not files:
        print("Папка steps пуста или файлы не найдены.")
        return
    
    # Создаём общий граф
    full_graph = nx.DiGraph()
    
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                analysis = json.load(f)
            
            # Генерируем slice_id из имени файла (step_19.json → slice_19)
            filename = os.path.basename(filepath)
            slice_id = filename.replace('.json', '')
            
            slice_graph = build_graph_from_slice(analysis, slice_id)
            
            # Объединяем в общий граф (сохраняем все узлы и рёбра)
            full_graph = nx.compose(full_graph, slice_graph)
            
            print(f"✓ Добавлен {slice_id}")
            
        except Exception as e:
            print(f"✗ Ошибка при обработке {filepath}: {e}")
    
    print(f"\nОбщий граф построен. Узлов: {len(full_graph.nodes())}, Рёбер: {len(full_graph.edges())}")
    
    # ====================== ИНТЕРАКТИВНАЯ ВИЗУАЛИЗАЦИЯ (ИСПРАВЛЕНО) ======================
    net = Network(height="950px", 
                  width="100%", 
                  directed=True, 
                  bgcolor="#0f0f1e", 
                  font_color="#ffffff",
                  notebook=False,           # ← Важно!
                  cdn_resources='remote')   # ← Рекомендуется для обычного скрипта

    # Добавляем узлы с разными цветами
    for node, data in full_graph.nodes(data=True):
        node_type = data.get('type', 'Entity')
        title = data.get('title', node)
        
        if node_type == "Source":
            color = "#ff6b6b"      # красный — источники (шаги)
            size = 28
        elif node == "Bot":
            color = "#4ecdc4"      # бирюзовый — центральный узел
            size = 48
        elif node_type == "Action":
            color = "#f9ca24"      # жёлтый — действия
            size = 20
        elif node_type == "KeyPhrase":
            color = "#a55eea"      # фиолетовый
            size = 22
        else:
            color = "#45b7d1"
            size = 24
        
        net.add_node(str(node), 
                     label=data.get('label', str(node)),
                     title=title,
                     color=color,
                     size=size)

    # Добавляем рёбра
    for u, v, data in full_graph.edges(data=True):
        label = data.get('label', data.get('relation', ''))
        net.add_edge(str(u), str(v), 
                     label=label if label else None,
                     title=label,
                     color="#555577",
                     arrows="to")

    # Настройки физики
    net.set_options("""
    {
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -12000,
          "centralGravity": 0.4,
          "springLength": 180
        },
        "minVelocity": 0.8
      },
      "nodes": {
        "font": { "size": 14 }
      },
      "edges": {
        "font": { "size": 10 }
      }
    }
    """)

    # Сохраняем HTML
    output_file = "jammingbot_full_knowledge_graph.html"
    net.write_html(output_file)        # ← Лучше использовать write_html вместо show()
    
    print(f"\nГотово! Интерактивный граф сохранён в файл:")
    print(f"   → {output_file}")
    print("Откройте этот файл в браузере (двойной клик).")

if __name__ == "__main__":
    main()