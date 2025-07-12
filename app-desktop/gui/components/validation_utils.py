class ValidationUtils:
    @staticmethod
    def validate_configuration(config):
        """Validar configuración completa"""
        errors = []

        # Validar LDAP
        ldap_config = config.get('ldap', {})
        if not ldap_config.get('server', '').strip():
            errors.append("servidor LDAP")
        if not ldap_config.get('domain', '').strip():
            errors.append("dominio LDAP")

        # Validar API
        api_config = config.get('api', {})
        if not api_config.get('server_ip', '').strip():
            errors.append("servidor API")

        # Validar Dispositivo
        dispositivo_config = config.get('dispositivo', {})
        if not dispositivo_config.get('tablet_id', '').strip():
            errors.append("ID de tablet")
        if not dispositivo_config.get('plancha', '').strip():
            errors.append("plancha")

        # Validar Cámaras
        camaras_config = config.get('camaras', {})
        if not camaras_config.get('camera1_ip', '').strip():
            errors.append("IP cámara 1")
        if not camaras_config.get('camera2_ip', '').strip():
            errors.append("IP cámara 2")

        return errors

    @staticmethod
    def validate_required_fields(fields_dict):
        """Validar campos requeridos"""
        missing_fields = []
        for field_name, field_value in fields_dict.items():
            if not field_value.strip():
                missing_fields.append(field_name)
        return missing_fields

    @staticmethod
    def validate_ip_address(ip_address):
        """Validar formato de dirección IP"""
        import re
        if not ip_address.strip():
            return False

        # Patrón básico para IP:puerto o solo IP
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}(:\d{1,5})?$'
        return bool(re.match(ip_pattern, ip_address.strip()))

    @staticmethod
    def validate_port(port):
        """Validar número de puerto"""
        try:
            port_num = int(port)
            return 1 <= port_num <= 65535
        except (ValueError, TypeError):
            return False

    @staticmethod
    def validate_domain(domain):
        """Validar formato de dominio"""
        import re
        if not domain.strip():
            return False

        # Patrón básico para dominio
        domain_pattern = r'^[a-zA-Z0-9][a-zA-Z0-9\-\.]*[a-zA-Z0-9]$'
        return bool(re.match(domain_pattern, domain.strip()))

    @staticmethod
    def validate_tablet_id(tablet_id):
        """Validar formato de ID de tablet"""
        if not tablet_id.strip():
            return False

        # Al menos 3 caracteres, solo alfanuméricos y guiones
        return len(tablet_id.strip()) >= 3 and tablet_id.replace('-', '').replace('_', '').isalnum()

    @staticmethod
    def get_validation_message(validation_type, field_name, field_value):
        """Obtener mensaje de validación específico"""
        messages = {
            'required': f"El campo '{field_name}' es requerido",
            'ip': f"'{field_value}' no es una dirección IP válida",
            'port': f"'{field_value}' no es un puerto válido (1-65535)",
            'domain': f"'{field_value}' no es un dominio válido",
            'tablet_id': f"'{field_value}' no es un ID de tablet válido (mínimo 3 caracteres alfanuméricos)"
        }
        return messages.get(validation_type, f"Valor inválido en '{field_name}'")

    @staticmethod
    def validate_all_config_fields(config_data):
        """Validar todos los campos de configuración con validaciones específicas"""
        validation_errors = []

        # Validar dispositivo
        dispositivo = config_data.get('dispositivo', {})
        tablet_id = dispositivo.get('tablet_id', '')
        plancha = dispositivo.get('plancha', '')

        if not tablet_id.strip():
            validation_errors.append(ValidationUtils.get_validation_message(
                'required', 'ID de Tablet', tablet_id))
        elif not ValidationUtils.validate_tablet_id(tablet_id):
            validation_errors.append(ValidationUtils.get_validation_message(
                'tablet_id', 'ID de Tablet', tablet_id))

        if not plancha.strip():
            validation_errors.append(ValidationUtils.get_validation_message(
                'required', 'Plancha', plancha))

        # Validar API
        api = config_data.get('api', {})
        api_server = api.get('server_ip', '')

        if not api_server.strip():
            validation_errors.append(ValidationUtils.get_validation_message(
                'required', 'Servidor API', api_server))
        elif not ValidationUtils.validate_ip_address(api_server):
            validation_errors.append(ValidationUtils.get_validation_message(
                'ip', 'Servidor API', api_server))

        # Validar LDAP
        ldap = config_data.get('ldap', {})
        ldap_server = ldap.get('server', '')
        ldap_port = ldap.get('port', '')
        ldap_domain = ldap.get('domain', '')

        if not ldap_server.strip():
            validation_errors.append(ValidationUtils.get_validation_message(
                'required', 'Servidor LDAP', ldap_server))
        elif not ValidationUtils.validate_ip_address(ldap_server):
            validation_errors.append(ValidationUtils.get_validation_message(
                'ip', 'Servidor LDAP', ldap_server))

        if not ValidationUtils.validate_port(ldap_port):
            validation_errors.append(ValidationUtils.get_validation_message(
                'port', 'Puerto LDAP', ldap_port))

        if not ldap_domain.strip():
            validation_errors.append(ValidationUtils.get_validation_message(
                'required', 'Dominio LDAP', ldap_domain))
        elif not ValidationUtils.validate_domain(ldap_domain):
            validation_errors.append(ValidationUtils.get_validation_message(
                'domain', 'Dominio LDAP', ldap_domain))

        # Validar cámaras (opcional pero si se proporciona debe ser válida)
        camaras = config_data.get('camaras', {})
        camera1_ip = camaras.get('camera1_ip', '')
        camera2_ip = camaras.get('camera2_ip', '')

        if camera1_ip.strip() and not ValidationUtils.validate_ip_address(camera1_ip):
            validation_errors.append(ValidationUtils.get_validation_message(
                'ip', 'Cámara 1 IP', camera1_ip))

        if camera2_ip.strip() and not ValidationUtils.validate_ip_address(camera2_ip):
            validation_errors.append(ValidationUtils.get_validation_message(
                'ip', 'Cámara 2 IP', camera2_ip))

        return validation_errors
