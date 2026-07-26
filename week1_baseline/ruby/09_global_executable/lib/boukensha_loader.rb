# BoukenshaLoader resolves which step folder and config directory to use, then
# boots the REPL.
#
# Each setting is resolved independently in this order:
#   1. BOUKENSHA_PATH / BOUKENSHA_DIR environment variable
#   2. boukensha_path / boukensha_dir in ~/.boukensharc
#   3. The bundled lib / ~/.boukensha default
#
# Examples:
#   boukensha                                                              # uses bundled lib + ~/.boukensha
#   BOUKENSHA_PATH=~/Sites/boukensha/04_api_client boukensha              # loads step 4
#   BOUKENSHA_DIR=~/projects/mybot/.boukensha boukensha                   # custom config dir
require "yaml"
require "rubygems"
require_relative "boukensha/version"

module BoukenshaLoader
  # Absolute path to this gem's own bundled boukensha lib.
  BUNDLED_LIB = File.expand_path("../boukensha.rb", __FILE__)

  def self.rc_file
    File.expand_path("~/.boukensharc")
  end

  def self.load_rc
    return {} unless File.exist?(rc_file)

    parsed = YAML.safe_load(
      File.read(rc_file),
      permitted_classes: [],
      aliases: false
    )

    case parsed
    when Hash
      parsed
    when String
      # Backward compatibility with the original single-path format.
      { "boukensha_path" => parsed }
    when nil
      {}
    else
      abort "boukensha: #{rc_file} must contain a YAML mapping"
    end
  rescue Psych::SyntaxError => e
    abort "boukensha: invalid YAML in #{rc_file}: #{e.message}"
  end

  def self.expand_rc_path(path)
    return nil unless path.is_a?(String)
    return nil if path.strip.empty?

    File.expand_path(path, File.dirname(rc_file))
  end

  def self.resolve
    rc = load_rc

    # Apply this before requiring the selected implementation. An explicit
    # environment variable always wins over the rc file.
    rc_config_dir = expand_rc_path(rc["boukensha_dir"])
    ENV["BOUKENSHA_DIR"] = rc_config_dir if !ENV["BOUKENSHA_DIR"] && rc_config_dir

    source = ENV["BOUKENSHA_PATH"] || expand_rc_path(rc["boukensha_path"])
    return BUNDLED_LIB unless source

    dir = File.expand_path(source)
    main = File.join(dir, "lib", "boukensha.rb")
    return main if File.exist?(main)

    abort <<~MSG
      boukensha: no lib/boukensha.rb found at:
             #{dir}
             Check BOUKENSHA_PATH or #{rc_file}.
    MSG
  end

  def self.load_and_start_repl
    main = resolve
    step_dir = File.dirname(File.dirname(main))

    puts "[boukensha] loading from: #{step_dir}" if ENV["BOUKENSHA_DEBUG"]

    require main

    unless Boukensha.respond_to?(:repl)
      abort <<~MSG
        boukensha: the step at #{step_dir}
               does not support the interactive REPL (added in step 7).
               Run its examples directly, e.g.:
                 ruby #{step_dir}/examples/*.rb
               Or point BOUKENSHA_PATH at step 7 or later.
      MSG
    end

    Boukensha.repl
  end

  def self.version(io: $stdout)
    io.puts "boukensha #{Boukensha::VERSION}"
  end

  def self.doctor(io: $stdout)
    rc = load_rc
    implementation = resolve
    config_dir = ENV["BOUKENSHA_DIR"] ||
      expand_rc_path(rc["boukensha_dir"]) ||
      File.expand_path("~/.boukensha")
    settings_file = File.join(config_dir, "settings.yaml")
    settings = if File.exist?(settings_file)
                 YAML.safe_load(
                   File.read(settings_file),
                   permitted_classes: [],
                   aliases: false
                 ) || {}
               else
                 {}
               end
    player = settings.fetch("tasks", {}).fetch("player", {})
    provider = player["provider"]
    model = player["model"]
    credential_name = {
      "anthropic" => "ANTHROPIC_API_KEY",
      "openai" => "OPENAI_API_KEY",
      "gemini" => "GEMINI_API_KEY",
      "ollama_cloud" => "OLLAMA_API_KEY"
    }[provider]
    credential_ready = provider == "ollama" ||
      credential_present?(credential_name, File.join(config_dir, ".env"))
    executable_dir = File.join(Gem.user_dir, "bin")
    path_entries = ENV.fetch("PATH", "").split(File::PATH_SEPARATOR)

    io.puts "Boukensha doctor"
    io.puts "  version:           #{Boukensha::VERSION}"
    io.puts "  ruby:              #{RUBY_VERSION}"
    io.puts "  executable dir:    #{executable_dir}"
    io.puts "  executable on PATH: #{path_entries.include?(executable_dir) ? "yes" : "no"}"
    io.puts "  rc file:           #{rc_file}#{File.exist?(rc_file) ? "" : " (not found)"}"
    io.puts "  implementation:    #{implementation}"
    io.puts "  config dir:        #{config_dir}#{Dir.exist?(config_dir) ? "" : " (not found)"}"
    io.puts "  settings:          #{settings_file}#{File.exist?(settings_file) ? "" : " (not found)"}"
    io.puts "  provider:          #{provider || "(not configured)"}"
    io.puts "  model:             #{model || "(not configured)"}"
    io.puts "  credential ready:  #{credential_ready ? "yes" : "no"}"

    unless path_entries.include?(executable_dir)
      io.puts
      io.puts "Add the executable to this shell with:"
      io.puts %(  export PATH="#{executable_dir}:$PATH")
    end
  end

  def self.credential_present?(name, env_file)
    return true if name && ENV[name] && !ENV[name].strip.empty?
    return false unless name && File.exist?(env_file)

    File.foreach(env_file).any? do |line|
      key, value = line.strip.split("=", 2)
      key == name && value && !value.strip.delete_prefix('"').delete_suffix('"').empty?
    end
  end
  private_class_method :credential_present?
end
