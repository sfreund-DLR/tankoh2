

from tankoh2.design.existingdesigns import allDesignKeywords, defaultDesign

def test_unknownKeywordsInDefaultDesign():
    defaultKeysSet = set(defaultDesign.keys())
    assert len(defaultKeysSet.difference(allDesignKeywords)) == 0





