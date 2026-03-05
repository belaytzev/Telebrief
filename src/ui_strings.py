"""
UI string translations for Telebrief.

Provides get_ui_strings(language) which returns a dict of UI labels
in the requested language, falling back to English for unsupported languages.
"""

_ENGLISH_MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

_MONTH_NAMES: dict[str, list[str]] = {
    "English": _ENGLISH_MONTHS,
    "Russian": [
        "января",
        "февраля",
        "марта",
        "апреля",
        "мая",
        "июня",
        "июля",
        "августа",
        "сентября",
        "октября",
        "ноября",
        "декабря",
    ],
    "Spanish": [
        "Enero",
        "Febrero",
        "Marzo",
        "Abril",
        "Mayo",
        "Junio",
        "Julio",
        "Agosto",
        "Septiembre",
        "Octubre",
        "Noviembre",
        "Diciembre",
    ],
    "German": [
        "Januar",
        "Februar",
        "März",
        "April",
        "Mai",
        "Juni",
        "Juli",
        "August",
        "September",
        "Oktober",
        "November",
        "Dezember",
    ],
    "French": [
        "Janvier",
        "Février",
        "Mars",
        "Avril",
        "Mai",
        "Juin",
        "Juillet",
        "Août",
        "Septembre",
        "Octobre",
        "Novembre",
        "Décembre",
    ],
}


_STRINGS: dict[str, dict[str, str]] = {
    "English": {
        # formatter.py
        "daily_digest": "Daily Digest",
        "overview": "Brief Overview",
        "open_channel": "Open channel",
        "stats_header": "Statistics",
        "channels": "channels",
        "messages_processed": "messages processed",
        "digest_for": "Digest for",
        "period_last_hours": "Period: last {hours} hours",
        "messages_count": "Messages processed",
        "last_hours": "Last {hours} hours",
        "truncated": "...(truncated due to length limit)",
        "digest_completed": "Digest completed",
        "channels_processed": "Channels processed",
        "total_messages": "Total messages",
        "period": "Period",
        # bot_commands.py
        "cmd_start_desc": "Start the bot",
        "cmd_digest_desc": "Generate digest for 24 hours",
        "cmd_cleanup_desc": "Delete old digests",
        "cmd_status_desc": "Show status and settings",
        "cmd_help_desc": "Show help",
        "generating_digest": "⏳ Generating digest for the last 24 hours...\nThis may take 1-2 minutes.",
        "digest_done": "✅ Digest ready! Each channel sent as a separate message.",
        "digest_error": "❌ Error generating digest. Check logs for details.",
        "digest_exception": "❌ An error occurred while generating the digest. Check logs.",
        "cleaning_up": "🧹 Deleting previous digests...",
        "cleanup_done": "✅ Previous digests successfully deleted!",
        "cleanup_partial": "⚠️ Failed to delete some messages. Check logs for details.",
        "cleanup_error": "❌ Error during cleanup. Check logs.",
        "status_header": "📊 **Telebrief Status**\n",
        "provider_label": "🤖 Provider",
        "model_label": "🧠 Model",
        "channels_configured": "📺 Channels configured",
        "auto_cleanup_label": "🧹 Auto-cleanup",
        "enabled": "Enabled",
        "disabled": "Disabled",
        "next_digest": "⏰ Next digest",
        "scheduler_not_running": "⏰ Scheduler not running",
        "available_commands": "**Available commands:**",
        "help_title": "🤖 **Telebrief - Telegram Digest Generator**",
        "help_intro": "I automatically generate daily digests from your Telegram channels using AI.",
        "help_commands_header": "**Commands:**",
        "help_auto_mode": "**Automatic mode:**",
        "help_auto_desc": "Digest is automatically generated every day at {schedule}",
        "help_features": "**Features:**",
        "help_features_list": (
            "• Processing channels in any language\n"
            "• Output in {output_lang}\n"
            "• Smart summaries ({provider})\n"
            "• Links to original messages\n"
            "• Auto-cleanup of old digests (configurable)"
        ),
    },
    "Russian": {
        # formatter.py
        "daily_digest": "Ежедневный дайджест",
        "overview": "Краткий обзор",
        "open_channel": "Открыть канал",
        "stats_header": "Статистика",
        "channels": "каналов",
        "messages_processed": "сообщений обработано",
        "digest_for": "Дайджест за",
        "period_last_hours": "Период: последние {hours} часов",
        "messages_count": "Обработано сообщений",
        "last_hours": "За последние {hours} часов",
        "truncated": "...(усечено из-за лимита длины)",
        "digest_completed": "Дайджест завершён",
        "channels_processed": "Обработано каналов",
        "total_messages": "Всего сообщений",
        "period": "Период",
        # bot_commands.py
        "cmd_start_desc": "Начать работу с ботом",
        "cmd_digest_desc": "Сгенерировать дайджест за 24 часа",
        "cmd_cleanup_desc": "Удалить старые дайджесты",
        "cmd_status_desc": "Показать статус и настройки",
        "cmd_help_desc": "Показать справку",
        "generating_digest": "⏳ Генерирую дайджест за последние 24 часа...\nЭто может занять 1-2 минуты.",
        "digest_done": "✅ Дайджест готов! Каждый канал отправлен отдельным сообщением.",
        "digest_error": "❌ Ошибка при генерации дайджеста. Проверьте логи для деталей.",
        "digest_exception": "❌ Произошла ошибка при генерации дайджеста. Проверьте логи.",
        "cleaning_up": "🧹 Удаляю предыдущие дайджесты...",
        "cleanup_done": "✅ Предыдущие дайджесты успешно удалены!",
        "cleanup_partial": "⚠️ Не удалось удалить некоторые сообщения. Проверьте логи для деталей.",
        "cleanup_error": "❌ Произошла ошибка при очистке. Проверьте логи.",
        "status_header": "📊 **Статус Telebrief**\n",
        "provider_label": "🤖 Провайдер",
        "model_label": "🧠 Модель",
        "channels_configured": "📺 Каналов настроено",
        "auto_cleanup_label": "🧹 Автоочистка",
        "enabled": "Включена",
        "disabled": "Выключена",
        "next_digest": "⏰ Следующий дайджест",
        "scheduler_not_running": "⏰ Планировщик не запущен",
        "available_commands": "**Доступные команды:**",
        "help_title": "🤖 **Telebrief - Telegram Digest Generator**",
        "help_intro": "Я автоматически генерирую ежедневные дайджесты из ваших Telegram-каналов с помощью AI.",
        "help_commands_header": "**Команды:**",
        "help_auto_mode": "**Автоматический режим:**",
        "help_auto_desc": "Дайджест генерируется автоматически каждый день в {schedule}",
        "help_features": "**Возможности:**",
        "help_features_list": (
            "• Обработка каналов на любых языках\n"
            "• Вывод на {output_lang}\n"
            "• Умные суммаризации ({provider})\n"
            "• Ссылки на оригинальные сообщения\n"
            "• Автоматическая очистка старых дайджестов (настраивается)"
        ),
    },
    "Spanish": {
        # formatter.py
        "daily_digest": "Resumen Diario",
        "overview": "Resumen Breve",
        "open_channel": "Abrir canal",
        "stats_header": "Estadísticas",
        "channels": "canales",
        "messages_processed": "mensajes procesados",
        "digest_for": "Resumen del",
        "period_last_hours": "Período: últimas {hours} horas",
        "messages_count": "Mensajes procesados",
        "last_hours": "Últimas {hours} horas",
        "truncated": "...(truncado por límite de longitud)",
        "digest_completed": "Resumen completado",
        "channels_processed": "Canales procesados",
        "total_messages": "Total de mensajes",
        "period": "Período",
        # bot_commands.py
        "cmd_start_desc": "Iniciar el bot",
        "cmd_digest_desc": "Generar resumen de 24 horas",
        "cmd_cleanup_desc": "Eliminar resúmenes antiguos",
        "cmd_status_desc": "Mostrar estado y configuración",
        "cmd_help_desc": "Mostrar ayuda",
        "generating_digest": "⏳ Generando resumen de las últimas 24 horas...\nEsto puede tardar 1-2 minutos.",
        "digest_done": "✅ ¡Resumen listo! Cada canal enviado como mensaje separado.",
        "digest_error": "❌ Error al generar el resumen. Consulte los registros.",
        "digest_exception": "❌ Ocurrió un error al generar el resumen. Consulte los registros.",
        "cleaning_up": "🧹 Eliminando resúmenes anteriores...",
        "cleanup_done": "✅ ¡Resúmenes anteriores eliminados con éxito!",
        "cleanup_partial": "⚠️ No se pudieron eliminar algunos mensajes. Consulte los registros.",
        "cleanup_error": "❌ Error durante la limpieza. Consulte los registros.",
        "status_header": "📊 **Estado de Telebrief**\n",
        "provider_label": "🤖 Proveedor",
        "model_label": "🧠 Modelo",
        "channels_configured": "📺 Canales configurados",
        "auto_cleanup_label": "🧹 Limpieza automática",
        "enabled": "Habilitado",
        "disabled": "Deshabilitado",
        "next_digest": "⏰ Próximo resumen",
        "scheduler_not_running": "⏰ Programador no está en ejecución",
        "available_commands": "**Comandos disponibles:**",
        "help_title": "🤖 **Telebrief - Telegram Digest Generator**",
        "help_intro": "Genero automáticamente resúmenes diarios de tus canales de Telegram usando IA.",
        "help_commands_header": "**Comandos:**",
        "help_auto_mode": "**Modo automático:**",
        "help_auto_desc": "El resumen se genera automáticamente cada día a las {schedule}",
        "help_features": "**Características:**",
        "help_features_list": (
            "• Procesamiento de canales en cualquier idioma\n"
            "• Salida en {output_lang}\n"
            "• Resúmenes inteligentes ({provider})\n"
            "• Enlaces a los mensajes originales\n"
            "• Limpieza automática de resúmenes antiguos (configurable)"
        ),
    },
    "German": {
        # formatter.py
        "daily_digest": "Tägliche Zusammenfassung",
        "overview": "Kurzer Überblick",
        "open_channel": "Kanal öffnen",
        "stats_header": "Statistiken",
        "channels": "Kanäle",
        "messages_processed": "verarbeitete Nachrichten",
        "digest_for": "Zusammenfassung für",
        "period_last_hours": "Zeitraum: letzte {hours} Stunden",
        "messages_count": "Verarbeitete Nachrichten",
        "last_hours": "Letzte {hours} Stunden",
        "truncated": "...(gekürzt wegen Längenlimit)",
        "digest_completed": "Zusammenfassung abgeschlossen",
        "channels_processed": "Verarbeitete Kanäle",
        "total_messages": "Nachrichten gesamt",
        "period": "Zeitraum",
        # bot_commands.py
        "cmd_start_desc": "Bot starten",
        "cmd_digest_desc": "24-Stunden-Zusammenfassung erstellen",
        "cmd_cleanup_desc": "Alte Zusammenfassungen löschen",
        "cmd_status_desc": "Status und Einstellungen anzeigen",
        "cmd_help_desc": "Hilfe anzeigen",
        "generating_digest": "⏳ Erstelle Zusammenfassung der letzten 24 Stunden...\nDies kann 1-2 Minuten dauern.",
        "digest_done": "✅ Zusammenfassung fertig! Jeder Kanal als separate Nachricht gesendet.",
        "digest_error": "❌ Fehler beim Erstellen der Zusammenfassung. Protokolle prüfen.",
        "digest_exception": "❌ Beim Erstellen der Zusammenfassung ist ein Fehler aufgetreten. Protokolle prüfen.",
        "cleaning_up": "🧹 Lösche vorherige Zusammenfassungen...",
        "cleanup_done": "✅ Vorherige Zusammenfassungen erfolgreich gelöscht!",
        "cleanup_partial": "⚠️ Einige Nachrichten konnten nicht gelöscht werden. Protokolle prüfen.",
        "cleanup_error": "❌ Fehler beim Aufräumen. Protokolle prüfen.",
        "status_header": "📊 **Telebrief-Status**\n",
        "provider_label": "🤖 Anbieter",
        "model_label": "🧠 Modell",
        "channels_configured": "📺 Konfigurierte Kanäle",
        "auto_cleanup_label": "🧹 Automatische Bereinigung",
        "enabled": "Aktiviert",
        "disabled": "Deaktiviert",
        "next_digest": "⏰ Nächste Zusammenfassung",
        "scheduler_not_running": "⏰ Planer läuft nicht",
        "available_commands": "**Verfügbare Befehle:**",
        "help_title": "🤖 **Telebrief - Telegram Digest Generator**",
        "help_intro": "Ich erstelle automatisch tägliche Zusammenfassungen aus deinen Telegram-Kanälen mit KI.",
        "help_commands_header": "**Befehle:**",
        "help_auto_mode": "**Automatischer Modus:**",
        "help_auto_desc": "Zusammenfassung wird täglich automatisch um {schedule} erstellt",
        "help_features": "**Funktionen:**",
        "help_features_list": (
            "• Verarbeitung von Kanälen in beliebigen Sprachen\n"
            "• Ausgabe auf {output_lang}\n"
            "• Intelligente Zusammenfassungen ({provider})\n"
            "• Links zu Originalnachrichten\n"
            "• Automatische Bereinigung alter Zusammenfassungen (konfigurierbar)"
        ),
    },
    "French": {
        # formatter.py
        "daily_digest": "Résumé Quotidien",
        "overview": "Bref Aperçu",
        "open_channel": "Ouvrir la chaîne",
        "stats_header": "Statistiques",
        "channels": "chaînes",
        "messages_processed": "messages traités",
        "digest_for": "Résumé du",
        "period_last_hours": "Période : {hours} dernières heures",
        "messages_count": "Messages traités",
        "last_hours": "{hours} dernières heures",
        "truncated": "...(tronqué en raison de la limite de longueur)",
        "digest_completed": "Résumé terminé",
        "channels_processed": "Chaînes traitées",
        "total_messages": "Total des messages",
        "period": "Période",
        # bot_commands.py
        "cmd_start_desc": "Démarrer le bot",
        "cmd_digest_desc": "Générer le résumé des 24h",
        "cmd_cleanup_desc": "Supprimer les anciens résumés",
        "cmd_status_desc": "Afficher le statut et les paramètres",
        "cmd_help_desc": "Afficher l'aide",
        "generating_digest": "⏳ Génération du résumé des 24 dernières heures...\nCela peut prendre 1-2 minutes.",
        "digest_done": "✅ Résumé prêt ! Chaque chaîne envoyée comme message séparé.",
        "digest_error": "❌ Erreur lors de la génération du résumé. Vérifiez les journaux.",
        "digest_exception": "❌ Une erreur s'est produite lors de la génération du résumé. Vérifiez les journaux.",
        "cleaning_up": "🧹 Suppression des résumés précédents...",
        "cleanup_done": "✅ Résumés précédents supprimés avec succès !",
        "cleanup_partial": "⚠️ Échec de la suppression de certains messages. Vérifiez les journaux.",
        "cleanup_error": "❌ Erreur lors du nettoyage. Vérifiez les journaux.",
        "status_header": "📊 **Statut Telebrief**\n",
        "provider_label": "🤖 Fournisseur",
        "model_label": "🧠 Modèle",
        "channels_configured": "📺 Chaînes configurées",
        "auto_cleanup_label": "🧹 Nettoyage automatique",
        "enabled": "Activé",
        "disabled": "Désactivé",
        "next_digest": "⏰ Prochain résumé",
        "scheduler_not_running": "⏰ Planificateur non démarré",
        "available_commands": "**Commandes disponibles :**",
        "help_title": "🤖 **Telebrief - Telegram Digest Generator**",
        "help_intro": "Je génère automatiquement des résumés quotidiens de vos chaînes Telegram grâce à l'IA.",
        "help_commands_header": "**Commandes :**",
        "help_auto_mode": "**Mode automatique :**",
        "help_auto_desc": "Le résumé est généré automatiquement chaque jour à {schedule}",
        "help_features": "**Fonctionnalités :**",
        "help_features_list": (
            "• Traitement des chaînes dans toutes les langues\n"
            "• Sortie en {output_lang}\n"
            "• Résumés intelligents ({provider})\n"
            "• Liens vers les messages originaux\n"
            "• Nettoyage automatique des anciens résumés (configurable)"
        ),
    },
}


def get_ui_strings(language: str) -> dict[str, str]:
    """
    Return UI strings for the given language, falling back to English.

    Args:
        language: Language name (e.g. "Russian", "English", "Spanish")

    Returns:
        Dict mapping string keys to translated values
    """
    return _STRINGS.get(language, _STRINGS["English"])


def get_month_names(language: str) -> list[str]:
    """
    Return month names list for the given language, falling back to English.

    Args:
        language: Language name (e.g. "Russian", "English", "Spanish")

    Returns:
        List of 12 month name strings, January-indexed
    """
    return _MONTH_NAMES.get(language, _ENGLISH_MONTHS)
