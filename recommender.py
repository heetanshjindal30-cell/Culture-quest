def _is_hidden_gem(loc):
    v = loc.get("type of location","").lower()
    return "hidden" in v or "local" in v

def _keywords(loc):
    text = " ".join([loc.get("Vibe Description",""),loc.get("detailed description",""),
                     loc.get("Category",""),loc.get("food to try","")]).lower()
    stop = {"a","an","the","is","in","of","to","and","for","with","at","on","it","this","that","by","from","are"}
    return {w for w in text.split() if len(w)>3 and w not in stop}

def _score(candidate, history_locs):
    if not history_locs: return 0
    total = 0.0
    c_cat,c_city,c_gem,c_kw = candidate.get("Category","").lower(),candidate.get("City","").lower(),_is_hidden_gem(candidate),_keywords(candidate)
    for seen in history_locs:
        if seen.get("Category","").lower()==c_cat: total+=3
        if seen.get("City","").lower()==c_city:    total+=2
        if _is_hidden_gem(seen)==c_gem:            total+=2
        total += len(c_kw & _keywords(seen))
    return total/len(history_locs)

def get_recommendations(history, all_locations, top_n=5):
    if not history or not all_locations:
        gems = [l for l in all_locations if _is_hidden_gem(l)]
        return gems[:top_n] if gems else all_locations[:top_n]
    viewed = {n.lower() for n in history}
    hist_locs = [l for l in all_locations if l.get("Place Name","").lower() in viewed]
    scored = sorted([(s,l) for l in all_locations if (s:=_score(l,hist_locs)) is not None
                     and l.get("Place Name","").lower() not in viewed],
                    key=lambda x:x[0], reverse=True)
    results = [l for _,l in scored[:top_n]]
    if not any(_is_hidden_gem(r) for r in results):
        gems = [l for l in all_locations if _is_hidden_gem(l) and l.get("Place Name","").lower() not in viewed]
        if gems: results[-1] = gems[0]
    return results

def explain_recommendation(candidate, history_locs):
    if not history_locs: return "Top hidden gem"
    reasons = []
    c_cat,c_city,c_kw = candidate.get("Category","").lower(),candidate.get("City","").lower(),_keywords(candidate)
    for seen in history_locs:
        if seen.get("Category","").lower()==c_cat:
            reasons.append(f"Similar to {seen.get('Place Name','')}"); break
    for seen in history_locs:
        if seen.get("City","").lower()==c_city:
            reasons.append(f"Also in {candidate.get('City','')}"); break
    if _is_hidden_gem(candidate): reasons.append("Hidden gem")
    return " · ".join(reasons[:2]) if reasons else "You might like this"
