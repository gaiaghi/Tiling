# Seamless Tiling Tool (STT)

STT (*Seamless Tiling Tool*) è un'applicazione standalone sviluppata in Python per generare texture seamless a partire da immagini PBR di tessuti digitalizzati.

Il software individua automaticamente moduli di ripetizione coerenti e consente di verificarne il risultato tramite un'anteprima di tiling. L'elaborazione viene eseguita in modo coordinato sulle mappe PBR associate, come albedo, normal e roughness.

## Funzionalità principali

- Ricerca automatica del modulo di ripetizione tramite confronto dei bordi e sliding window.
- Supporto per selezioni rettangolari e a parallelogramma.
- Generazione di anteprime di tiling 3×3.
- Subpatching per la correzione di artefatti e discontinuità locali.
- Utilizzo di Graph Cut e algoritmi min-cut/max-flow per la fusione delle patch.
- Elaborazione coerente delle mappe PBR associate.
- Salvataggio dei moduli estratti e dei risultati nella cartella di output senza modificare i file originali.

## Requisiti

- Python 3.12 o versione compatibile.
- Le dipendenze Python elencate in `requirements.txt`.
- Mappe PBR in formato PNG o JPEG, con uguale risoluzione e allineamento pixel a pixel.

Le principali librerie utilizzate sono NumPy, SciPy, Pillow, Tkinter, scikit-image, Matplotlib e NetworkX.

## Installazione, utilizzo e documentazione

Per una descrizione completa del progetto, dell'architettura, degli algoritmi, dei risultati sperimentali e delle limitazioni si rimanda al report finale.


## Riferimenti

- V. Kwatra et al., *Graphcut Textures: Image and Video Synthesis Using Graph Cuts*, 2003.
- [Suffoquer-fang/GraphCut](https://github.com/Suffoquer-fang/GraphCut)
- [lzqsd/TileableTextureSynthesis](https://github.com/lzqsd/TileableTextureSynthesis)

