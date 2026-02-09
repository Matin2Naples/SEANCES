import React, { useState, useEffect } from 'react';
import { Plus } from 'lucide-react';

const SeanceApp = () => {
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [showCinemaSelector, setShowCinemaSelector] = useState(false);
  const [showtimesData, setShowtimesData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedFilm, setExpandedFilm] = useState(null); // Format: "cinema-filmIdx"
  
  // URL du backend - change ça quand tu déploieras
  const API_URL = 'http://localhost:5001';
  
  // Cinémas sélectionnés (sera synchronisé avec le backend)
  const [selectedCinemas, setSelectedCinemas] = useState([
    'Christine Cinéma Club',
    'Filmothèque du Quartier Latin',
    'La Cinémathèque',
    'Le Champo',
    'Le Grand Action',
    'Le Louxor',
    'MK2 Quai de Loire',
    'MK2 Quai de Seine',
    'Reflet Médicis',
    'Écoles Cinéma Club',
    'UGC Les Halles',
  ]);

  const [allCinemas, setAllCinemas] = useState([]);

  // Charger la liste des cinémas disponibles
  useEffect(() => {
    fetch(`${API_URL}/cinemas`)
      .then(res => res.json())
      .then(data => {
        setAllCinemas(data.cinemas);
      })
      .catch(err => {
        console.error('Erreur chargement cinémas:', err);
      });
  }, []);

  // Charger les horaires à chaque changement de date
  useEffect(() => {
    loadShowtimes();
  }, [selectedDate]);

  const loadShowtimes = async () => {
    setLoading(true);
    setError(null);
    
    const dateStr = selectedDate.toISOString().split('T')[0];
    
    try {
      const response = await fetch(`${API_URL}/showtimes?date=${dateStr}`);
      if (!response.ok) throw new Error('Erreur API');
      
      const data = await response.json();
      setShowtimesData(data.showtimes);
      setLoading(false);
    } catch (err) {
      setError('Impossible de charger les horaires');
      setLoading(false);
      console.error(err);
    }
  };

  const toggleCinema = (cinema) => {
    if (selectedCinemas.includes(cinema)) {
      setSelectedCinemas(selectedCinemas.filter(c => c !== cinema));
    } else {
      setSelectedCinemas([...selectedCinemas, cinema]);
    }
  };

  const getNextDays = () => {
    const days = [];
    for (let i = 0; i < 7; i++) {
      const date = new Date();
      date.setDate(date.getDate() + i);
      days.push(date);
    }
    return days;
  };

  const formatDate = (date) => {
    return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long' });
  };

  const toggleFilmExpansion = (cinema, filmIdx) => {
    const filmKey = `${cinema}-${filmIdx}`;
    setExpandedFilm(expandedFilm === filmKey ? null : filmKey);
  };

  const formatReleaseDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.getFullYear();
  };

  // Écran de sélection des cinémas
  if (showCinemaSelector) {
    return (
      <div style={{ 
        fontFamily: 'Helvetica, Arial, sans-serif',
        backgroundColor: '#929299',
        minHeight: '100vh'
      }}>
        <div style={{
          position: 'sticky',
          top: 0,
          backgroundColor: '#000000',
          color: '#e2e4e8',
          padding: '20px',
          zIndex: 100
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            position: 'relative'
          }}>
            <div style={{ fontSize: '24px', fontWeight: '400', color: '#c1ff00' }}>Séance(s)</div>
            <div style={{ 
              position: 'absolute',
              left: '50%',
              fontSize: '24px', 
              color: '#ffffff'
            }}>
              {formatDate(selectedDate)}
            </div>
            <Plus 
              size={20} 
              color="#929299" 
              style={{ 
                cursor: 'pointer',
                transform: 'rotate(45deg)',
                transition: 'transform 0.3s'
              }}
              onClick={() => setShowCinemaSelector(false)}
            />
          </div>
        </div>

        <div>
          {allCinemas.map((cinema, idx) => (
            <div
              key={idx}
              onClick={() => toggleCinema(cinema)}
              style={{
                padding: '20px',
                fontSize: '24px',
                fontWeight: '400',
                color: '#000000',
                backgroundColor: selectedCinemas.includes(cinema) ? '#c1ff00' : '#929299',
                borderBottom: '1px solid #000000',
                cursor: 'pointer',
                transition: 'background-color 0.2s'
              }}
            >
              {cinema}
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Écran principal
  return (
    <div style={{ 
      fontFamily: 'Helvetica, Arial, sans-serif',
      backgroundColor: '#929299',
      minHeight: '100vh',
      paddingBottom: '40px'
    }}>
      {/* Header */}
      <div style={{
        position: 'sticky',
        top: 0,
        backgroundColor: '#000000',
        color: '#e2e4e8',
        padding: '20px',
        zIndex: 100
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          position: 'relative'
        }}>
          <div style={{ fontSize: '24px', fontWeight: '400', color: '#c1ff00' }}>Séance(s)</div>
          <div 
            onClick={() => setShowDatePicker(!showDatePicker)}
            style={{ 
              position: 'absolute',
              left: '50%',
              fontSize: '24px', 
              color: '#ffffff',
              cursor: 'pointer',
              userSelect: 'none'
            }}
          >
            {formatDate(selectedDate)}
          </div>
          <Plus 
            size={20} 
            color="#929299" 
            style={{ 
              cursor: 'pointer',
              transition: 'transform 0.3s'
            }}
            onClick={() => setShowCinemaSelector(true)}
          />
        </div>
      </div>

      {/* Date Picker */}
      {showDatePicker && (
        <div style={{
          position: 'sticky',
          top: '68px',
          backgroundColor: '#929299',
          zIndex: 99
        }}>
          {getNextDays().map((date, idx) => (
            <div
              key={idx}
              onClick={() => {
                setSelectedDate(date);
                setShowDatePicker(false);
              }}
              style={{
                padding: '20px',
                paddingLeft: '50%',
                fontSize: '24px',
                cursor: 'pointer',
                color: '#000000',
                backgroundColor: date.toDateString() === selectedDate.toDateString() ? '#c1ff00' : '#929299',
                borderBottom: '1px solid #000000',
                transition: 'background-color 0.2s'
              }}
            >
              {formatDate(date)}
            </div>
          ))}
        </div>
      )}

      {/* Chargement */}
      {loading && (
        <div style={{
          padding: '40px',
          textAlign: 'center',
          fontSize: '18px',
          color: '#000000'
        }}>
          <div style={{ marginBottom: '16px' }}>Chargement des horaires...</div>
          <div style={{ fontSize: '14px', color: '#666' }}>Cela peut prendre 20-30 secondes</div>
        </div>
      )}

      {/* Erreur */}
      {error && (
        <div style={{
          padding: '40px',
          textAlign: 'center',
          fontSize: '18px',
          color: '#ff0000'
        }}>
          {error}
          <div 
            onClick={loadShowtimes}
            style={{
              marginTop: '16px',
              padding: '12px 24px',
              backgroundColor: '#000000',
              color: '#ffffff',
              cursor: 'pointer',
              display: 'inline-block',
              borderRadius: '4px'
            }}
          >
            Réessayer
          </div>
        </div>
      )}

      {/* Liste des cinémas et films */}
      {!loading && !error && showtimesData && selectedCinemas.map((cinema, cinemaIdx) => {
        const films = showtimesData[cinema] || [];
        
        if (films.length === 0) return null;
        
        return (
          <div key={cinemaIdx}>
            {/* Header du cinéma */}
            <div style={{
              position: 'sticky',
              top: '68px',
              backgroundColor: '#929299',
              padding: '20px',
              fontSize: '24px',
              fontWeight: '400',
              color: '#000000',
              borderBottom: '1px solid #000000',
              zIndex: 50
            }}>
              {cinema}
            </div>

            {/* Films */}
            {films.map((film, filmIdx) => {
              const filmKey = `${cinema}-${filmIdx}`;
              const isExpanded = expandedFilm === filmKey;
              
              return (
                <div 
                  key={filmIdx}
                  style={{
                    backgroundColor: '#929299',
                    borderBottom: '1px solid #000000',
                    padding: '20px',
                    position: 'relative'
                  }}
                >
                  {/* Info film - Vue compacte */}
                  {!isExpanded && (
                    <>
                      <div style={{
                        fontFamily: '"EB Garamond", serif',
                        fontSize: '16px',
                        lineHeight: '18px',
                        color: '#000000',
                        maxWidth: '45%'
                      }}>
                        <div style={{ 
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          marginBottom: '2px'
                        }}>
                          {film.title}
                        </div>
                        <div style={{ 
                          fontWeight: '600',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          marginBottom: '12px'
                        }}>
                          {film.director}
                        </div>
                        <div>{film.duration}</div>
                      </div>

                      {/* Horaires - Vue compacte */}
                      <div style={{
                        position: 'absolute',
                        left: '50%',
                        top: '20px'
                      }}>
                        <div style={{
                          fontFamily: '"EB Garamond", serif',
                          fontSize: '16px',
                          lineHeight: '18px',
                          color: '#000000',
                          textAlign: 'left'
                        }}>
                          {film.showtimes.map((time, timeIdx) => (
                            <div key={timeIdx} style={{ marginBottom: timeIdx < film.showtimes.length - 1 ? '4px' : '0' }}>
                              <span style={{ fontWeight: '600' }}>{time.start}</span>
                              <span> (→ {time.end})</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </>
                  )}

                  {/* Info film - Vue étendue */}
                  {isExpanded && (
                    <div style={{ display: 'flex', gap: '20px' }}>
                      {/* Colonne gauche : infos textuelles */}
                      <div style={{ flex: 1 }}>
                        <div style={{
                          fontFamily: '"EB Garamond", serif',
                          fontSize: '16px',
                          lineHeight: '18px',
                          color: '#000000'
                        }}>
                          {/* Titre et réalisateur */}
                          <div style={{ marginBottom: '2px' }}>
                            {film.title}
                          </div>
                          <div style={{ fontWeight: '600', marginBottom: '12px' }}>
                            {film.director}
                          </div>

                          {/* Genres (max 2) */}
                          {film.genres && film.genres.length > 0 && (
                            <div style={{ marginBottom: '2px' }}>
                              {film.genres.map((genre, idx) => (
                                <div key={idx}>{genre}</div>
                              ))}
                            </div>
                          )}

                          {/* Durée */}
                          <div style={{ marginBottom: '12px' }}>{film.duration}</div>

                          {/* Date de sortie */}
                          {film.release_date && (
                            <div style={{ marginBottom: '12px' }}>
                              {formatReleaseDate(film.release_date)}
                            </div>
                          )}

                          {/* Acteurs */}
                          {film.actors && film.actors.length > 0 && (
                            <div>
                              <div style={{ marginBottom: '4px' }}>Avec :</div>
                              {film.actors.slice(0, 5).map((actor, idx) => (
                                <div key={idx}>{actor}</div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Colonne droite : affiche */}
                      {film.poster_url && (
                        <div style={{ 
                          width: '50%',
                          display: 'flex',
                          justifyContent: 'flex-end'
                        }}>
                          <img 
                            src={film.poster_url} 
                            alt={film.title}
                            style={{
                              width: '100%',
                              height: 'auto',
                              objectFit: 'cover'
                            }}
                          />
                        </div>
                      )}
                    </div>
                  )}

                  {/* Horaires en bas quand étendu */}
                  {isExpanded && (
                    <div style={{
                      marginTop: '20px',
                      fontFamily: '"EB Garamond", serif',
                      fontSize: '16px',
                      lineHeight: '18px',
                      color: '#000000',
                      textAlign: 'right'
                    }}>
                      {film.showtimes.map((time, timeIdx) => (
                        <div key={timeIdx} style={{ marginBottom: timeIdx < film.showtimes.length - 1 ? '4px' : '0' }}>
                          <span style={{ fontWeight: '600' }}>{time.start}</span>
                          <span> (→ {time.end})</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Bouton + / - */}
                  <Plus 
                    size={20} 
                    color="#000000" 
                    style={{ 
                      cursor: 'pointer',
                      position: 'absolute',
                      right: '20px',
                      top: '20px',
                      transform: isExpanded ? 'rotate(45deg) translateY(-2px)' : 'translateY(-2px)',
                      transition: 'transform 0.3s'
                    }}
                    onClick={() => toggleFilmExpansion(cinema, filmIdx)}
                  />
                </div>
              );
            })}
          </div>
        );
      })}
    </div>
  );
};

export default SeanceApp;