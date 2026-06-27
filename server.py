if ($path === 'estado_conexion' && $_SERVER['REQUEST_METHOD'] === 'GET') {
    $heartbeat_file = __DIR__ . '/heartbeat.json';
    $estado = [];
    
    if (file_exists($heartbeat_file)) {
        $data = json_decode(file_get_contents($heartbeat_file), true);
        $online = $data['estado'] === 'online' && 
                  (time() - strtotime($data['last_update'])) < 60;
        
        $agentes_ids = ['agata' => 4, 'lucia' => 5, 'orion' => 6];
        foreach ($agentes_ids as $nombre => $id) {
            $estado[$id] = $online && in_array($nombre, $data['perfiles']);
        }
    } else {
        $estado = [4 => true, 5 => true, 6 => true];
    }
    
    echo json_encode($estado);
    exit;
}
